#!/usr/bin/env python3
import argparse
import os
import threading
import time
from project_manager import Job
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

    def run_benchmark(self):
        import random
        self.cpu_score = random.randrange(1, 10)
        self.net_score = random.randrange(1, 10)
        self.cpu_score = float(os.popen("./bench-host.sh morro " + str(self.address)).read())
        print("node", self.address, "CPU:", self.cpu_score)

    def run(self):
        threading.Thread(target=self.__run).start()

    def __run(self):
        while True:
            j = project_manager.get_job(self.cpu_score)
            if j.job_weight == -1:
                print(self.address, "\tterminating...")
                return
            self.run_job(j)

    def run_job(self, j):
        print(self.address + "\trunning job: ", j.job_path, "\tWeight: ", j.job_weight)
        # time.sleep(0.5)
        job_path = j.job_path[:j.job_path.rfind("/")]

        os.system("./render-on-host.sh \"" + job_path + "\" morro " + str(self.address))


def get_render_nodes():
    with open('nodes.txt') as fp:
        return fp.read().splitlines()


if __name__ == '__main__':

    if args.folder is None:
        print("usage: --folder <folder>")
        exit()

    # creating random dummy jobs
    # import random
    # for i in range(10):
    #     jobs.append(Job(i, random.randrange(1, 10)))

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
