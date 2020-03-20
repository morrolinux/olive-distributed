#!/usr/bin/env python3
import socket
from worker_node import WorkerNode
import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpu", dest='gpu', action='store_true', help="use the GPU for encoding " +
                                                                       "(ffmpeg only) for this instance.")
    parser.set_defaults(gpu=False)
    args = parser.parse_args()

    node = WorkerNode(socket.gethostname())
    node.setup(gpu=args.gpu)
    node.run()
