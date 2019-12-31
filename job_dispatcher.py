import Pyro4.core
from job import Job
import threading
from worker_node import WorkerNode
import os
import math
from Pyro4.util import SerializerBase
from ssl_utils import CertCheckingProxy, CertValidatingDaemon
from ssl_utils import LOCAL_HOSTNAME, SSL_CERTS_DIR


class JobDispatcher:
    Pyro4.config.SSL = True
    Pyro4.config.SSL_REQUIRECLIENTCERT = True  # 2-way ssl
    Pyro4.config.SSL_SERVERCERT = SSL_CERTS_DIR + LOCAL_HOSTNAME + ".crt"
    Pyro4.config.SSL_SERVERKEY = SSL_CERTS_DIR + LOCAL_HOSTNAME + ".key"
    Pyro4.config.SSL_CACERTS = SSL_CERTS_DIR + "rootCA.crt"  # to make ssl accept the self-signed master cert

    # For using NFS mounter as a client
    Pyro4.config.SSL_CLIENTCERT = Pyro4.config.SSL_SERVERCERT
    Pyro4.config.SSL_CLIENTKEY = Pyro4.config.SSL_SERVERKEY

    print(Pyro4.config.SSL_CLIENTCERT)

    def __init__(self, jobs):
        self.d = None
        self.jobs = jobs
        self.split_job = None
        self.parts_lock = threading.Lock()
        self.workers = []
        SerializerBase.register_dict_to_class("worker_node.WorkerNode", WorkerNode.node_dict_to_class)
        self.nfs_exporter = CertCheckingProxy('PYRO:NfsExporter@localhost:9091')
        self.first_run = True

    @Pyro4.expose
    def test(self):
        return "connection ok"

    @Pyro4.expose
    def get_worker_options(self):
        # options = {"nfs_tuning": ['-o', 'noacl,nocto,noatime,nodiratime']}
        options = {"nfs_tuning": ['-o', 'async']}
        return options

    @Pyro4.expose
    def join_work(self, node):
        self.workers.append(node)

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

    @Pyro4.expose
    def report(self, node, job, exit_status, export_range=None):
        print("NODE", node.address, "completed job", job.job_path, "with status", exit_status)
        # If the export fails, re-insert it in the job queue
        if exit_status != 0 and export_range is None:
            self.jobs.append(job)
        # If the failed export was part of a split job, re-insert the failed range
        elif exit_status != 0 and export_range is not None:
            self.split_job.fail(export_range)
        # If the split job export went fine, move the exported range to the completed ones
        elif self.split_job is not None and export_range is not None:
            self.split_job.complete(export_range)

        # In any case, always remove the share after a worker is done
        self.nfs_exporter.unexport(job.job_path, to=node.address)

        if self.split_job is not None and self.split_job.split_job_finished():
            self.merge_parts(self.split_job.job_path[self.split_job.job_path.rfind("/") + 1:])
            print("Export merged. Finished!!!")
            self.jobs.remove(self.split_job)
            self.d.shutdown()

    @Pyro4.expose
    def get_job(self, n):
        abort = Job("abort", -1)

        if len(self.jobs) <= 0:
            print("PROJECT MANAGER: no more work to do")
            return abort, None, None, None

        if self.first_run:
            import time
            print("waiting to see if any other workers are joining us...")
            time.sleep(5)
            self.first_run = False

        # Assign a job based on node benchmark score
        max_score = max(node.cpu_score for node in self.workers)
        min_score = min(node.cpu_score for node in self.workers)
        max_weight = max(job.job_weight for job in self.jobs)
        min_weight = min(job.job_weight for job in self.jobs)
        fuzzy_job_weight = 0

        if max_score != min_score:
            fuzzy_job_weight = min_weight + ((max_weight - min_weight) / (max_score - min_score)) * (n.cpu_score - min_score)

        assigned_job = min(self.jobs, key=lambda x: abs(x.job_weight - fuzzy_job_weight))

        if assigned_job is None:
            return abort, None, None, None

        # Slow tail fix:
        # if there are more nodes than jobs, check weather a faster node is about to finish its work before assignment
        # if so, don't assign the current job to the current (slower) node and terminate it.
        # TODO: with Pyro, workers in self.render nodes are not updated from remote and cannot provide useful ETA
        if len(self.jobs) < len(self.workers) and not assigned_job.split:
            for worker in self.workers:
                w_eta = worker.job_eta() + worker.job_eta(assigned_job)
                n_eta = n.job_eta(assigned_job)
                if w_eta < n_eta:
                    return abort, None, None, None

        # If the extracted job is a split job, assign the current worker a chunk
        if assigned_job.split:
            self.parts_lock.acquire()
            self.split_job = assigned_job

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
                    return abort, None, None, None

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

            # Export the folder via NFS so that the worker node can access it
            self.nfs_exporter.export(self.split_job.job_path, to=n.address)

            # Beware the possible race condition that could happen if parts,start,end
            # get changed just after releasing this lock and before returning them to the worker
            self.parts_lock.release()

            # Return the job to the worker node
            return self.split_job, str(job_name), job_start, job_end

        # Export the folder via NFS so that the worker node can access it
        self.nfs_exporter.export(assigned_job.job_path, to=n.address)

        print(n.address + "\trunning job: ", assigned_job.job_path[assigned_job.job_path.rfind("/")+1:],
              "\tWeight: ", assigned_job.job_weight)
        self.jobs.remove(assigned_job)
        return assigned_job, None, None, None

    def start(self):
        try:
            self.nfs_exporter.test()
        except Pyro4.errors.CommunicationError as e:
            print("Can't connect to local NFS exporter service, make sure it's running.\n", e)
            return

        self.d = CertValidatingDaemon(host=LOCAL_HOSTNAME, port=9090)
        test_uri = self.d.register(self, "JobDispatcher")
        print("Job dispatcher ready. URI:", test_uri)
        self.d.requestLoop()

