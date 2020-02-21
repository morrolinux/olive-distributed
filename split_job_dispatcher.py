import Pyro4.core
from job_dispatcher import JobDispatcher
import threading
from job import Job, abort_job, ExportRange
from Pyro4.util import SerializerBase
import os
import math
import time
import random


class SplitJobDispatcher(JobDispatcher):
    def __init__(self):
        super().__init__()
        self.split_job = None
        self.parts_lock = threading.Lock()
        self.worker_fails = dict()
        self.ongoing_ranges = set()
        self.failed_ranges = set()
        self.completed_ranges = set()
        self.last_assigned_frame = 0
        self.job_parts = 0
        SerializerBase.register_dict_to_class("job.ExportRange", ExportRange.export_range_dict_to_class)
        SerializerBase.register_class_to_dict(ExportRange, ExportRange.export_range_class_to_dict)

    def set_ongoing_range(self, r):
        r.reset_instance()
        self.ongoing_ranges.add(r)
        try:
            self.failed_ranges.remove(r)
        except KeyError:
            pass

    def fail_range(self, export_range):
        self.failed_ranges.add(export_range)
        try:
            self.ongoing_ranges.remove(export_range)
        except KeyError:
            pass
        # TODO: cleanup potential part files with instance name

    def complete_range(self, export_range):
        self.completed_ranges.add(export_range)
        try:
            self.failed_ranges.remove(export_range)
        except KeyError:
            pass

    def split_job_finished(self):
        if len(self.completed_ranges) == 0:
            total_len_covered = False
        else:
            total_len_covered = self.split_job.len == max(n.end for n in self.completed_ranges)
        all_parts_done = self.job_parts == len(self.completed_ranges)
        no_failed_ranges = len(self.failed_ranges) == 0
        return total_len_covered and all_parts_done and no_failed_ranges

    def write_concat_list(self, list_name):
        with open(list_name, "w") as m:
            parts = list(self.completed_ranges)
            parts.sort()
            for p in parts:
                m.write("file \'" + str(p.instance_id) + ".mp4\'\n")

            # for p in range(1, len(self.completed_ranges) + 1):
            #     m.write("file \'" + str(p) + ".mp4\'\n")

    def merge_parts(self, output_name):
        os.chdir(self.split_job.job_path[:self.split_job.job_path.rfind("/")])
        list_name = "merge.txt"
        self.write_concat_list(list_name)
        os.system("ffmpeg -f concat -safe 0 -i " + list_name + " -c copy " + output_name + ".mp4" + " -y")
        os.remove(list_name)
        for p in self.completed_ranges:
            os.remove(str(p.instance_id) + ".mp4")

    def remove_shares(self):
        for worker in self.workers:
            self.nfs_exporter.unexport(self.split_job.job_path, to=worker.address)

    @Pyro4.expose
    def join_work(self, node):
        super().join_work(node)
        self.worker_fails[node.address] = []
        self.nfs_exporter.export(self.split_job.job_path, to=node.address)

    @Pyro4.expose
    def report(self, node, job, exit_status, export_range):
        print(" ", node.address, "completed part", export_range, "with status:", exit_status)

        # If someone else already completed this job, just discard it
        if export_range in self.completed_ranges:
            # TODO: remove file from disk
            pass
        # Otherwise, if export failed, re-insert failed ranges
        elif exit_status != 0:
            self.fail_range(export_range)
            self.worker_fails[node.address].append(export_range)
        # If the split job export went fine, move the exported range to the completed ones
        else:
            self.complete_range(export_range)

        if self.split_job_finished():
            self.remove_shares()
            self.merge_parts(self.split_job.job_path[self.split_job.job_path.rfind("/") + 1:])
            print("Export merged. Finished!!!")
            self.daemon.shutdown()

    @Pyro4.expose
    def get_job(self, n):
        if self.split_job_finished():
            return abort_job, None

        if self.first_run:
            print("Welcome, " + str(n.address) + ".\n waiting to see if any other workers are joining us...")
            time.sleep(5)
            self.first_run = False

        # TODO: maybe implement an adapted version of slow tail fix for part assignment

        self.parts_lock.acquire()

        # Assign the given worker a chunk size proportional to its rank
        tot_workers_score = sum(worker.cpu_score for worker in self.workers)
        if len(self.workers) > 1:
            s = 900
            chunk_size = s + math.ceil((n.cpu_score / tot_workers_score) * s)
        else:
            chunk_size = 1800

        # Where to start/end the chunk (+ update seek)
        # TODO: Make sure to ALWAYS match keyframes... (should probably be done in Olive)
        job_start = self.last_assigned_frame
        job_end = min(job_start + chunk_size, self.split_job.len)
        self.last_assigned_frame = job_end

        # If we're still working but all frames have been assigned, check if there are failed ranges left
        if job_end - job_start == 0:
            # If there are no failed jobs left, we are really done.

            if len(self.failed_ranges) > 0:
                r = list(self.failed_ranges)[random.randrange(0, len(self.failed_ranges)) % len(self.failed_ranges)]
                # If a worker has already failed this specific range, don't attempt again
                if r in self.worker_fails[n.address]:
                    self.parts_lock.release()
                    return Job("retry", 1), None
                self.set_ongoing_range(r)
                print("Retrying failed part:", r)
            # If there still are ongoing jobs, they *could* belong to crashed workers.
            # We therefore assign them anyways. The first worker to finish will move them to the terminated set
            elif len(self.ongoing_ranges) > 0:
                # Extracting one random job so that if there are multiple ongoing ones we don't assign the same to all
                r = list(self.ongoing_ranges)[random.randrange(0, len(self.ongoing_ranges)) % len(self.ongoing_ranges)]
            # If there are no more failed nor ongoing jobs, we really are finished.
            else:
                self.parts_lock.release()
                return Job("abort", 0), None

        else:
            # update the current number of job parts
            self.job_parts += 1
            r = ExportRange(self.job_parts, job_start, job_end)
            self.ongoing_ranges.add(r)

        print(n.address, "will export part", r)

        # Beware the possible race condition that could happen if parts,start,end
        # get changed just after releasing this lock and before returning them to the worker
        self.parts_lock.release()

        # Return the job to the worker node
        try:
            return self.split_job, r
        except TypeError as e:
            print(e)
            print(r)
            print(dir(r))

