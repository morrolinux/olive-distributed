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
        self.split_workers = 0
        self.split_workers_lock = threading.Lock()
        self.split_workers_done = 0
        self.split_workers_done_lock = threading.Lock()
        self.split_job = None
        self.split_job_parts = 0
        self.parts_lock = threading.Lock()
        self.workers = []
        self.__test_counter = 0
        SerializerBase.register_dict_to_class("worker_node.WorkerNode", WorkerNode.node_dict_to_class)
        self.nfs_exporter = CertCheckingProxy('PYRO:NfsExporter@localhost:9091')

    @Pyro4.expose
    def test(self):
        self.__test_counter += 1
        return "connection ok ("+str(self.__test_counter)+")"

    @Pyro4.expose
    def join_work(self, node):
        self.workers.append(node)

    def write_concat_list(self, list_name):
        with open(list_name, "w") as m:
            for p in range(1, self.split_job_parts + 1):
                m.write("file \'" + str(p) + ".mp4\'\n")

    def merge_parts(self, output_name):
        os.chdir(self.split_job.job_path[:self.split_job.job_path.rfind("/")])
        list_name = "merge.txt"
        self.write_concat_list(list_name)
        os.system("ffmpeg -f concat -safe 0 -i " + list_name + " -c copy " + output_name + ".mp4" + " -y")
        os.remove(list_name)
        for p in range(1, self.split_job_parts + 1):
            os.remove(str(p) + ".mp4")

    @Pyro4.expose
    def report(self, node, job, exit_status):
        print("NODE", node.address, "completed job", job.job_path, "with status", exit_status)
        # If the export fails, re-insert it in the job queue
        # TODO: handle export range recovery for part jobs
        if exit_status != 0:
            self.jobs.append(job)
        elif self.split_job is not None:
            self.split_workers_done_lock.acquire()
            self.split_workers_done = self.split_workers_done + 1
            self.split_workers_done_lock.release()

        # In any case, always remove the share after a worker is done
        self.nfs_exporter.unexport(job.job_path, to=node.address)

        if self.split_job_finished() and self.all_split_workers_done():
            self.merge_parts(self.split_job.job_path[self.split_job.job_path.rfind("/") + 1:])
            print("Export merged. Finished!!!")
            self.d.shutdown()

    def split_job_finished(self):
        if self.split_job is None:
            return False
        return self.split_job.len == self.split_job.last_rendered_frame

    def all_split_workers_done(self):
        if self.split_job is None:
            return False
        if self.split_workers == self.split_workers_done:
            return True
        else:
            return False

    @Pyro4.expose
    def get_job(self, n):
        abort = Job("abort", -1)

        if len(self.jobs) <= 0:
            print("PROJECT MANAGER: no more work to do")
            return abort, None, None, None

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
            tot_workers_score = 0
            for worker in self.workers:
                tot_workers_score = tot_workers_score + worker.cpu_score
            # chunk_size = math.ceil((n.cpu_score / tot_workers_score) * self.split_job.len)
            chunk_size = math.ceil(900)

            # where to start/end the chunk (and update seek)
            job_start = self.split_job.last_rendered_frame
            job_end = min(job_start + chunk_size, self.split_job.len)
            # TODO: Make sure to ALWAYS end on a keyframe... (should probably be done in Olive)
            self.split_job.last_rendered_frame = job_end

            # Increment the numer of workers who are taking part of the split job..
            self.split_workers_lock.acquire()
            self.split_workers = self.split_workers + 1
            self.split_workers_lock.release()

            # update the current number of job parts
            self.split_job_parts = self.split_job_parts + 1

            print(n.address, "will export", self.split_job.job_path, "from", job_start, "to", job_end,
                  "- part", self.split_job_parts, "(", job_end - job_start, "frames )")

            if self.split_job.len == job_end:
                self.jobs.remove(assigned_job)
                # TODO: probably don't need to save self.split and remove it from the queue, but instead
                #  keep it until termination condition (at the beginning of this procedure) is reached.
            self.parts_lock.release()

            # Export the folder via NFS so that the worker node can access it
            self.nfs_exporter.export(self.split_job.job_path, to=n.address)
            # Return the job to the worker node
            return self.split_job, str(self.split_job_parts), job_start, job_end

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

