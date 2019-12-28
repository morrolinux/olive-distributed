import Pyro4.core
from ssl_utils import CertValidatingDaemon
import socket


class NfsExporter:
    Pyro4.config.SSL = True
    Pyro4.config.SSL_REQUIRECLIENTCERT = True  # 2-way ssl
    Pyro4.config.SSL_SERVERCERT = "ssl/certs/localhost.crt"
    Pyro4.config.SSL_SERVERKEY = "ssl/certs/localhost.key"
    Pyro4.config.SSL_CACERTS = "ssl/certs/rootCA.crt"  # to make ssl accept the self-signed master cert

    @Pyro4.expose
    def test(self):
        return "ok"

    @Pyro4.expose
    def export(self, path, to=None):
        print("exporting", path)

    @Pyro4.expose
    def unexport(self, path, to=None):
        print("unexporting", path)

    def start(self):
        d = CertValidatingDaemon(port=9091)
        uri = d.register(self, "NfsExporter")
        print("NFS Exporter ready. URI:", uri)
        d.requestLoop()


if __name__ == '__main__':
    nfsExporter = NfsExporter()
    nfsExporter.start()
