#!/usr/bin/env python3
import argparse
import os
import threading
import time

parser = argparse.ArgumentParser()
parser.add_argument("--folder", dest='folder', help="folder containing projects folders")
args = parser.parse_args()

jobs = []
render_nodes = []


class Job:
    def __init__(self, job_path, job_weight):
        self.job_path = job_path
        self.job_weight = job_weight


class RenderNode:
    def __init__(self, address):
        self.address = address
        self.cpu_score = 0
        self.net_score = 0

    def run_benchmark(self):
        import random
        # self.cpu_score = random.randrange(1, 10)
        self.net_score = random.randrange(1, 10)
        self.cpu_score = float(os.popen("./bench-host.sh morro " + self.address).read())
        print("node", self.address, "CPU:", self.cpu_score)

    def run(self):
        threading.Thread(target=self.__run).start()

    def __run(self):
        while True:
            j = get_job(self.cpu_score)
            if j.job_weight == -1:
                print("exiting!!!")
                return
            self.run_job(j)

    def run_job(self, j):
        print(self.address + "\trunning job: ", j.job_path, "\tWeight: ", j.job_weight)
        # time.sleep(0.5)
        os.system("./render-on-host.sh \"" + j.job_path + "\" morro " + self.address)


def get_subdirs(mydir):
    return [name for name in os.listdir(mydir) if os.path.isdir(os.path.join(mydir, name))]


def get_render_nodes():
    with open('nodes.txt') as fp:
        return fp.read().splitlines()


def get_job(node_rank):
    # TODO: implement some logic for assigning the job according to the node rank (and pop elements)
    if len(jobs) <= 0:
        return Job("-1", -1)

    max_score = max(node.cpu_score for node in render_nodes)
    min_score = min(node.cpu_score for node in render_nodes)
    max_weight = max(job.job_weight for job in jobs)
    min_weight = min(job.job_weight for job in jobs)
    print("max weight:", max_weight, "\nmin weight:", min_weight)

    tmp = Job("-1", -1)

    # TODO: improve classification
    if node_rank > (max_score + min_score)/2:
        for j in jobs:
            if j.job_weight >= (max_weight + min_weight)/2:
                tmp = j
                jobs.remove(j)
                break
    else:
        for j in jobs:
            if j.job_weight <= (max_weight + min_weight)/2:
                tmp = j
                jobs.remove(j)
                break

    return tmp


if __name__ == '__main__':

    if args.folder is None:
        print("usage: --folder <folder>")
        exit()

    # creating random dummy jobs
    # import random
    # for i in range(10):
    #     jobs.append(Job(i, random.randrange(1, 10)))

    for d in get_subdirs(args.folder):
        jobs.append(Job(args.folder + d, 10))

    # instantiate (and benchmark) a new node object for each node found in list
    benchmark_threads = []
    for n in get_render_nodes():
        render_nodes.append(RenderNode(n))
        benchmark_threads.append(threading.Thread(target=render_nodes[-1].run_benchmark))
        benchmark_threads[-1].start()

    # wait for benchmark results from all hosts
    for b in benchmark_threads:
        b.join()

    # start nodes
    for n in render_nodes:
        n.run()

    # TODO: wait for all the threads to finish
