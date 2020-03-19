#!/usr/bin/env python3
import argparse
from project_manager import ProjectManager
from full_job_dispatcher import FullJobDispatcher
from split_job_dispatcher import SplitJobDispatcher
from global_settings import settings

parser = argparse.ArgumentParser()
parser.add_argument("--folder", dest='folder', help="folder containing projects folders")
parser.add_argument("--project", dest='project', help="project file to be rendered on multiple nodes")
parser.add_argument("--video", dest='video', help="video file to be compressed on multiple nodes")
parser.add_argument("--ffmpeg-options", dest='ffmpeg_options', help="ffmpeg codec options. Defaults are \"" +
                                                                    " ".join(settings.ffmpeg['encoder']) + "\"")
parser.add_argument("--chunk-size", dest='chunk_size', help="base chunk size (in seconds) for which to split the video "
                                                            "across the nodes. Use larger chunks for longer videos. "
                                                            "Default: " + str(settings.dispatcher['chunk_size']) + "\n")
parser.add_argument("--gpu", dest='gpu', action='store_true', help="wether or not to use the GPU for encoding " +
                                                                   "(ffmpeg only) - this invalidates ffmpeg-options.")
parser.add_argument("--gpu-options", dest='gpu_options', help="wether or not to use the GPU for encoding " +
                                                              "(ffmpeg only) - this invalidates ffmpeg-options. " +
                                                              "Defaults: \"" +
                                                              " ".join(settings.ffmpeg['gpu_encoder']) + "\"")
parser.set_defaults(gpu=False)

args = parser.parse_args()


def get_render_nodes():
    with open('nodes.txt') as fp:
        return fp.read().splitlines()


if __name__ == '__main__':

    if args.folder is None and args.project is None and args.video is None:
        print("usage: --folder <folder> | --project <file> | --video <file>")
        exit()

    # initialize the project manager with the render nodes
    project_manager = ProjectManager()

    # and feed it the job(s) to be done
    job_dispatcher = None
    if args.chunk_size is not None:
        settings.dispatcher['chunk_size'] = int(args.chunk_size)
    if args.folder is not None:
        settings.dispatcher["workflow"] = "full"
        settings.dispatcher["job_type"] = "project"
        project_manager.explore(args.folder)
        job_dispatcher = FullJobDispatcher()
        job_dispatcher.jobs = project_manager.jobs
    elif args.project is not None:
        settings.dispatcher["workflow"] = "split"
        settings.dispatcher["job_type"] = "project"
        project_manager.add_project(args.project, part=True)
        job_dispatcher = SplitJobDispatcher()
        job_dispatcher.split_job = project_manager.jobs[0]
    elif args.video is not None:
        settings.dispatcher["workflow"] = "split"
        settings.dispatcher["job_type"] = "ffmpeg"
        if args.ffmpeg_options is not None:
            settings.ffmpeg["encoder"] = args.ffmpeg_options.split()
        if args.gpu:
            settings.ffmpeg["gpu"] = True
            if args.gpu_options is not None:
                settings.ffmpeg["gpu_encoder"] = args.gpu_options.split()
        project_manager.add_video(args.video)
        job_dispatcher = SplitJobDispatcher()
        job_dispatcher.split_job = project_manager.jobs[0]
    else:
        print("invalid options")
        exit()

    job_dispatcher.start()
