import argparse
import os
import threading

parser = argparse.ArgumentParser()
parser.add_argument("--folder", dest='folder', help="folder containing projects folders")
args = parser.parse_args()


class RenderThread:
    def __init__(self, node_id):
        self.node_id = node_id

    def run(self):
        while True:
            j = get_job()
            if j == -1:
                return
            self.run_job()

    def run_job(self):
        pass


def get_subdirs(mydir):
    return [name for name in os.listdir(mydir) if os.path.isdir(os.path.join(mydir, name))]


def get_job(node_rank):
    # TODO: implement some logic for assigning the job according to the node rank
    # TODO: pop the element
    pass


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
        # TODO: istanzio una classe node_x.x.x.x e lancio il thread
        # threading.Thread(target=self.check_remotes).start()
        pass

    # TODO: resto in attesa per tutti i thread rimanenti (semaforo?)

    '''
    print("starting batch")
    for subdir in get_subdirs(args.folder):
        proj = args.folder + subdir
        print("rendering", proj)
        # os.system("./render-on-host.sh " + proj + " morro " +  )
    '''



