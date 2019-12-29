import Pyro4.core
from ssl_utils import CertValidatingDaemon, SSL_CERTS_DIR
import subprocess
import socket


class NfsMounter:
    Pyro4.config.SSL = True
    Pyro4.config.SSL_REQUIRECLIENTCERT = True  # 2-way ssl
    Pyro4.config.SSL_SERVERCERT = SSL_CERTS_DIR + socket.gethostname() + "_local.crt"
    Pyro4.config.SSL_SERVERKEY = SSL_CERTS_DIR + socket.gethostname() + "_local.key"
    Pyro4.config.SSL_CACERTS = SSL_CERTS_DIR + "rootCA.crt"  # to make ssl accept the self-signed master cert

    @Pyro4.expose
    def test(self):
        return "ok"

    @staticmethod
    def __nfs4_syntax(path, address):
        # get the enclosing folder of the project
        if path.find(".ove") > 0:
            path = path[:path.rfind("/")]
        # add server address prefix
        path = address+":"+path
        return path

    @Pyro4.expose
    def mount(self, path, address, mountpoint):
        path = self.__nfs4_syntax(path, address)
        print("mounting", path)
        if subprocess.run(['mount', path, mountpoint, '-w'], stdout=subprocess.PIPE).returncode != 0:
            print("There was an error mounting", path, "- I might not be able to access media.")
            return -1
        return 0

    @Pyro4.expose
    def umount(self, mountpoint):
        print("umounting", mountpoint)
        if subprocess.run(['umount', mountpoint], stdout=subprocess.PIPE).returncode != 0:
            print("There was an error umounting", mountpoint, "- media might still be accessible.")
            return -1
        return 0

    def start(self):
        d = CertValidatingDaemon(port=9092)
        uri = d.register(self, "NfsMounter")
        print("NFS Mounter ready. URI:", uri)
        d.requestLoop()


if __name__ == '__main__':
    nfsMounter = NfsMounter()
    nfsMounter.start()
