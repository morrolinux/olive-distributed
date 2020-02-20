#!/usr/bin/env python3
import argparse
from project_manager import ProjectManager
from full_job_dispatcher import FullJobDispatcher
from split_job_dispatcher import SplitJobDispatcher
from global_settings import settings

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
    job_dispatcher = None
    if args.folder is not None:
        settings.dispatcher["workflow"] = "full"
        project_manager.explore(args.folder)
        job_dispatcher = FullJobDispatcher()
        job_dispatcher.jobs = project_manager.jobs
    elif args.project is not None:
        settings.dispatcher["workflow"] = "split"
        project_manager.add(args.project, part=True)
        job_dispatcher = SplitJobDispatcher()
        job_dispatcher.split_job = project_manager.jobs[0]
    else:
        print("invalid options")
        exit()

    job_dispatcher.start()
