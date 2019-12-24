#!/usr/bin/env python3
import socket
from render_node import RenderNode


if __name__ == '__main__':
    node = RenderNode(socket.gethostname())
    node.run()
