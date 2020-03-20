import Pyro4.core
from ssl_utils import CertValidatingDaemon, SSL_CERTS_DIR
import subprocess
import socket
import os


class NfsMounter:
    Pyro4.config.SSL = True
    Pyro4.config.SSL_REQUIRECLIENTCERT = True  # 2-way ssl
    Pyro4.config.SSL_SERVERCERT = SSL_CERTS_DIR + socket.gethostname() + "_local.crt"
    Pyro4.config.SSL_SERVERKEY = SSL_CERTS_DIR + socket.gethostname() + "_local.key"
    Pyro4.config.SSL_CACERTS = SSL_CERTS_DIR + "rootCA.crt"  # to make ssl accept the self-signed master cert

    def __init__(self):
        self._mounts = set()

    @Pyro4.expose
    def test(self):
        return "ok"

    @staticmethod
    def __nfs4_syntax(path, address):
        # get the enclosing folder of the project
        # TODO: refactor this into a more flexible and less hacky lookup
        if ".ove" in path or ".mp4" in path:
            path = path[:path.rfind("/")]
        # add server address prefix
        path = address+":"+path
        return path

    @Pyro4.expose
    def mount(self, path, address, mountpoint, nfs_options):
        try:
            os.mkdir(mountpoint)
        except FileExistsError:
            pass
        path = self.__nfs4_syntax(path, address)
        mount_options = ['mount', path, mountpoint, '-w'] + nfs_options

        # Don't mount twice
        if ' '.join(mount_options) in self._mounts:
            return 0

        print("mounting", path)
        mounter = subprocess.run(mount_options, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if mounter.returncode != 0:
            print("There was an error mounting", path, "- I might not be able to access media.")
            print(mounter.stdout, mounter.stderr)
            self.umount(mountpoint)
            return -1
        self._mounts.add(''.join(mount_options))
        print(self._mounts)
        return 0

    @Pyro4.expose
    def umount(self, mountpoint):
        print("umounting", mountpoint)
        if subprocess.run(['umount', '-f', mountpoint], stdout=subprocess.PIPE).returncode != 0:
            print("There was an error umounting", mountpoint, "- media might still be accessible.")
            return -1
        self._mounts.clear()
        return 0

    def start(self):
        d = CertValidatingDaemon(port=9092)
        uri = d.register(self, "NfsMounter")
        print("NFS Mounter ready. URI:", uri)
        d.requestLoop()


if __name__ == '__main__':
    nfsMounter = NfsMounter()
    nfsMounter.start()
