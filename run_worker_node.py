#!/usr/bin/env python3
import socket
from worker_node import WorkerNode


if __name__ == '__main__':
    node = WorkerNode(socket.gethostname())
    node.setup()
    node.run()
