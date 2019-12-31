import Pyro4.core
from job_dispatcher import JobDispatcher
import threading
from job import Job, abort_job
import os
import math


class SplitJobDispatcher(JobDispatcher):
    def __init__(self):
        super().__init__()
        self.split_job = None
        self.parts_lock = threading.Lock()

    def write_concat_list(self, list_name):
        with open(list_name, "w") as m:
            for p in range(1, len(self.split_job.completed_ranges) + 1):
                m.write("file \'" + str(p) + ".mp4\'\n")

    def merge_parts(self, output_name):
        os.chdir(self.split_job.job_path[:self.split_job.job_path.rfind("/")])
        list_name = "merge.txt"
        self.write_concat_list(list_name)
        os.system("ffmpeg -f concat -safe 0 -i " + list_name + " -c copy " + output_name + ".mp4" + " -y")
        os.remove(list_name)
        for p in range(1, len(self.split_job.completed_ranges) + 1):
            os.remove(str(p) + ".mp4")

    def remove_shares(self):
        for worker in self.workers:
            self.nfs_exporter.unexport(self.split_job.job_path, to=worker.address)

    @Pyro4.expose
    def report(self, node, job, exit_status, export_range):
        print("NODE", node.address, "completed part", export_range, "with status", exit_status)
        # If export failed, re-insert the failed range
        if exit_status != 0:
            self.split_job.fail(export_range)
        # If the split job export went fine, move the exported range to the completed ones
        else:
            self.split_job.complete(export_range)

        if self.split_job.split_job_finished():
            self.remove_shares()
            self.merge_parts(self.split_job.job_path[self.split_job.job_path.rfind("/") + 1:])
            print("Export merged. Finished!!!")
            self.daemon.shutdown()

    @Pyro4.expose
    def join_work(self, node):
        super().join_work(node)
        self.nfs_exporter.export(self.split_job.job_path, to=node.address)

    @Pyro4.expose
    def get_job(self, n):
        if self.first_run:
            import time
            print("waiting to see if any other workers are joining us...")
            time.sleep(5)
            self.first_run = False

        # TODO: maybe implement an adapted version of slow tail fix for part assignment

        self.parts_lock.acquire()

        # assign the given worker a chunk size proportional to its rank
        tot_workers_score = sum(worker.cpu_score for worker in self.workers)
        if len(self.workers) > 1:
            s = 1000
            chunk_size = s + math.ceil((n.cpu_score / tot_workers_score) * s)
        else:
            chunk_size = 1800

        # where to start/end the chunk (and update seek)
        # TODO: Make sure to ALWAYS match keyframes... (should probably be done in Olive)
        job_start = self.split_job.last_assigned_frame
        job_end = min(job_start + chunk_size, self.split_job.len)
        self.split_job.last_assigned_frame = job_end

        # If we're still working but all frames have been assigned, check if there are failed ranges left
        if job_end - job_start == 0:
            # If there are not failed jobs left, we are really done.
            if len(self.split_job.failed_ranges) == 0:
                self.parts_lock.release()
                return abort_job, None, None, None

            r = self.split_job.failed_ranges.popitem()
            print("Retrying failed part:", r)
            job_name = r[0]
            job_start = r[1][0]
            job_end = r[1][1]
        else:
            # update the current number of job parts
            self.split_job.parts = self.split_job.parts + 1
            job_name = self.split_job.parts

        print(n.address, "will export from", job_start, "to", job_end,
              "- part", job_name, "(", job_end - job_start, "frames )")

        # Beware the possible race condition that could happen if parts,start,end
        # get changed just after releasing this lock and before returning them to the worker
        self.parts_lock.release()

        # Return the job to the worker node
        return self.split_job, str(job_name), job_start, job_end
