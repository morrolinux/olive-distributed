#!/usr/bin/env python3
import argparse
import threading
from project_manager import ProjectManager
from render_node import RenderNode

parser = argparse.ArgumentParser()
parser.add_argument("--folder", dest='folder', help="folder containing projects folders")
parser.add_argument("--project", dest='project', help="project file to be rendered on multiple nodes")
args = parser.parse_args()


def get_render_nodes():
    with open('nodes.txt') as fp:
        return fp.read().splitlines()


if __name__ == '__main__':

    if args.folder is None and args.project is None:
        print("usage: --folder <folder> | --project <file>")
        exit()

    print("\n=============== Nodes Setup ===============")
    # instantiate (and benchmark) a new node object for each node found in list
    render_nodes = []
    benchmark_threads = []
    for n in get_render_nodes():
        render_nodes.append(RenderNode(n))
        benchmark_threads.append(threading.Thread(target=render_nodes[-1].run_benchmark))
        benchmark_threads[-1].start()

    # initialize the project manager with the render nodes
    project_manager = ProjectManager(render_nodes)
    # and feed it the job(s) to be done
    if args.folder is not None:
        project_manager.explore(args.folder)
    elif args.project is not None:
        project_manager.add(args.project, part=True)

    # wait for benchmark results from all hosts
    for b in benchmark_threads:
        b.join()

    # start nodes
    print("\n============ Starting Nodes ===============")
    for n in render_nodes:
        n.run()

