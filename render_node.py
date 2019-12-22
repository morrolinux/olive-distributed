import threading
import time
import Pyro4


class RenderNode:
    def __init__(self, address):
        self.address = address
        self.cpu_score = 0
        self.net_score = 0
        self.__job_start_time = None
        self.__job = None
        self.sample_weight = None
        self.sample_time = None
        self.project_manager = None
        self.node_service = Pyro4.core.Proxy('PYRO:NodeService@' + self.address + ':9090')

    def set_manager(self, manager):
        self.project_manager = manager

    def job_eta(self, j=None):
        if self.sample_time is None or self.sample_weight is None:
            return 9223372036854775807

        if j is not None:
            t = (j.job_weight * self.sample_time) / self.sample_weight
        elif self.__job is not None:
            t = self.job_eta(self.__job) - (time.time() - self.__job_start_time)
        else:
            t = 0
        return t

    def run_benchmark(self):
        try:
            self.cpu_score = self.node_service.run_benchmark()
        except Pyro4.errors.CommunicationError:
            print("node", self.address, "is unreachable and won't be used.")
            self.cpu_score = -1
            self.net_score = -1
            return
        print("node", self.address, "\t\tCPU:", self.cpu_score)

    def run(self):
        threading.Thread(target=self.__run).start()

    def __run(self):
        while True:
            j, name, start, end = self.project_manager.get_job(self)
            if j.job_path == "abort":
                print(self.address, "\tterminating...")
                return
            if j.job_path == "retry":
                time.sleep(j.job_weight)
                continue
            self.run_job(j, name, start, end)

    def run_job(self, j, name, start, end):
        self.__job = j

        print(self.address + "\trunning job: ", j.job_path[j.job_path.rfind("/")+1:],
              "\tWeight: ", j.job_weight, "\tETA:", round(self.job_eta()), "s.")

        simulation_wait = (j.job_weight/self.cpu_score)/500

        self.__job_start_time = time.time()
        self.node_service.run_job(j.job_path, name, start, end, wait=simulation_wait)
        self.sample_time = time.time() - self.__job_start_time

        self.sample_weight = j.job_weight
        self.sample_time = time.time() - self.__job_start_time
        self.__job = None
