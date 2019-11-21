#!/usr/bin/env python3
import argparse
import os
import threading
import time

parser = argparse.ArgumentParser()
parser.add_argument("--folder", dest='folder', help="folder containing projects folders")
args = parser.parse_args()

# dummy job list
jobs = [1, 2, 3, 4, 5, 6, 7, 8, 9]


class RenderNode:
    def __init__(self, address):
        self.address = address
        self.cpu_score = 0
        self.net_score = 0
        print("node ", address, "created")

    def run_benchmark(self):
        # TODO: run an actual benchmark on remote host and get results
        self.cpu_score = 100
        self.net_score = 100

    def run(self):
        threading.Thread(target=self.__run).start()

    def __run(self):
        while True:
            j = get_job(self.cpu_score)
            if j == -1:
                print("exiting!!!")
                return
            self.run_job(j)

    def run_job(self, j):
        print(self.address + " running job", j)
        # os.system("./render-on-host.sh " + j + " morro " + self.address)
        time.sleep(0.5)


def get_subdirs(mydir):
    return [name for name in os.listdir(mydir) if os.path.isdir(os.path.join(mydir, name))]


def get_job(node_rank):
    # TODO: implement some logic for assigning the job according to the node rank (and pop elements)
    try:
        return jobs.pop()
    except IndexError:
        return -1


def get_render_nodes():
    with open('nodes.txt') as fp:
        return fp.read().splitlines()


if __name__ == '__main__':

    if args.folder is None:
        print("usage: --folder <folder>")
        exit()

    nodes = get_render_nodes()
    print("render nodes:", nodes)

    for n in nodes:
        # instantiate a new node object for each node found in list
        exec("node_" + n.replace(".", "_") + " = RenderNode(n)")
        exec("node_" + n.replace(".", "_") + ".run()")

    # TODO: wait for all the threads to finish
