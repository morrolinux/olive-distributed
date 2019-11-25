#!/usr/bin/env python3
import argparse
import os
import threading
import time
from project_manager import Job
import random
from project_manager import ProjectManager

parser = argparse.ArgumentParser()
parser.add_argument("--folder", dest='folder', help="folder containing projects folders")
args = parser.parse_args()

render_nodes = []
project_manager = None


class RenderNode:
    def __init__(self, address):
        self.address = address
        self.cpu_score = 0
        self.net_score = 0
        self.__job_start_time = None
        self.__job = None
        self.sample_weight = None
        self.sample_time = None

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
        import random
        self.cpu_score = random.randrange(1, 10)
        self.net_score = random.randrange(1, 10)
        self.cpu_score = float(os.popen("./bench-host.sh morro " + str(self.address)).read())
        print("node", self.address, "\tCPU:", self.cpu_score)

    def run(self):
        threading.Thread(target=self.__run).start()

    def __run(self):
        while True:
            j = project_manager.get_job(self)
            if j.job_path == "abort":
                print(self.address, "\tterminating...")
                return
            if j.job_path == "retry":
                time.sleep(j.job_weight)
                continue
            self.run_job(j)

    def run_job(self, j):
        job_folder = j.job_path[:j.job_path.rfind("/")]
        self.__job_start_time = time.time()
        self.__job = j
        print(self.address + "\trunning job: ", j.job_path[j.job_path.rfind("/")+1:],
              "\tWeight: ", j.job_weight, "\tETA:", round(self.job_eta()), "s.")

        # time.sleep((j.job_weight/self.cpu_score)/100)
        os.system("./render-on-host.sh \"" + job_folder + "\" morro " + str(self.address))

        self.sample_weight = j.job_weight
        self.sample_time = time.time() - self.__job_start_time
        self.__job = None
        self.__job_start_time


def get_render_nodes():
    with open('nodes.txt') as fp:
        return fp.read().splitlines()


if __name__ == '__main__':

    if args.folder is None:
        print("usage: --folder <folder>")
        exit()

    # instantiate (and benchmark) a new node object for each node found in list
    print("\n=============== Nodes Setup ===============")
    benchmark_threads = []
    for n in get_render_nodes():
        render_nodes.append(RenderNode(n))
        benchmark_threads.append(threading.Thread(target=render_nodes[-1].run_benchmark))
        benchmark_threads[-1].start()

    project_manager = ProjectManager(render_nodes)
    project_manager.explore(args.folder)

    # wait for benchmark results from all hosts
    for b in benchmark_threads:
        b.join()

    # start nodes
    print("\n============ Starting Nodes ===============")
    for n in render_nodes:
        n.run()

    # TODO: wait for all the threads to finish
