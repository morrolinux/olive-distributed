#!/usr/bin/env python3
import argparse
import threading
from project_manager import ProjectManager
from render_node import RenderNode
import time
from job_dispatcher import JobDispatcher

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

    # initialize the project manager with the render nodes
    project_manager = ProjectManager()

    # and feed it the job(s) to be done
    if args.folder is not None:
        project_manager.explore(args.folder)
    elif args.project is not None:
        project_manager.add(args.project, part=True)

    job_dispatcher = JobDispatcher(project_manager.jobs)
    job_dispatcher.start()
