import Pyro4.core
import socket
from job import Job
import threading
from render_node import RenderNode
import os


class JobDispatcher:
    Pyro4.config.SSL = True
    Pyro4.config.SSL_REQUIRECLIENTCERT = True  # 2-way ssl
    Pyro4.config.SSL_SERVERCERT = "ssl/certs/node_cert.pem"
    Pyro4.config.SSL_SERVERKEY = "ssl/certs/node_key.pem"
    Pyro4.config.SSL_CACERTS = "ssl/certs/master_cert.pem"  # to make ssl accept the self-signed master cert

    class CertValidatingDaemon(Pyro4.core.Daemon):
        def validateHandshake(self, conn, data):
            cert = conn.getpeercert()
            # if not cert:
            #     raise Pyro4.errors.CommunicationError("node cert missing")
            return super(JobDispatcher.CertValidatingDaemon, self).validateHandshake(conn, data)

    def __init__(self, jobs):
        self.jobs = jobs
        self.split_nodes = []
        self.split_nodes_done = 0
        self.split_nodes_done_lock = threading.Lock()
        self.split_job = None
        self.split_job_parts = 0
        self.parts_lock = threading.Lock()
        self.render_nodes = []
        self.__test_counter = 0

    @Pyro4.expose
    def test(self):
        self.__test_counter += 1
        return "connection ok ("+str(self.__test_counter)+")"

    @Pyro4.expose
    def join_work(self, node):
        self.render_nodes.append(node)

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
    def get_job(self, n):
        abort = Job("abort", -1)

        # when a (split) node comes back asking for a job and the current one is finished, merge the parts and quit.
        if n in self.split_nodes and self.split_job.len == self.split_job.last_rendered_frame:
            self.split_nodes_done_lock.acquire()
            self.split_nodes_done = self.split_nodes_done + 1
            if self.split_nodes_done == len(self.render_nodes):
                self.merge_parts(self.split_job.job_path[self.split_job.job_path.rfind("/")+1:])
                print("Export merged. Finished!!!")
            self.split_nodes_done_lock.release()

        if len(self.jobs) <= 0:
            print("PROJECT MANAGER: no more work to do")
            return abort, None, None, None

        # Assign a job based on node benchmark score
        max_score = max(node.cpu_score for node in self.render_nodes)
        min_score = min(node.cpu_score for node in self.render_nodes)
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
        if len(self.jobs) < len(self.render_nodes) and not assigned_job.split:
            for worker in self.render_nodes:
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
            for worker in self.render_nodes:
                tot_workers_score = tot_workers_score + worker.cpu_score
            chunk_size = math.ceil((n.cpu_score / tot_workers_score) * self.split_job.len)

            # where to start/end the chunk (and update seek)
            job_start = self.split_job.last_rendered_frame
            job_end = min(job_start + chunk_size, self.split_job.len)
            # TODO: Make sure to ALWAYS end on a keyframe... (should probably be done in Olive)
            self.split_job.last_rendered_frame = job_end

            # append the given worker to the list of workers doing a split job
            self.split_nodes.append(n)
            # update the current number of job parts
            self.split_job_parts = self.split_job_parts + 1

            print(n.address, "will export", self.split_job.job_path, "from", job_start, "to", job_end,
                  "- part", self.split_job_parts, "(", job_end - job_start, "frames )")

            if self.split_job.len == job_end:
                self.jobs.remove(assigned_job)
                # TODO: probably don't need to save self.split and remove it from the queue, but instead
                #  keep it until termination condition (at the beginning of this procedure) is reached.
            self.parts_lock.release()
            return self.split_job, str(self.split_job_parts), job_start, job_end

        self.jobs.remove(assigned_job)
        return assigned_job, None, None, None

    def start(self):
        d = self.CertValidatingDaemon(host=socket.gethostname(), port=9090)
        test_uri = d.register(self, "JobDispatcher")
        print("test uri:", test_uri)
        d.requestLoop()
