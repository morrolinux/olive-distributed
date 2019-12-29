import Pyro4.core
from ssl_utils import CertValidatingDaemon, SSL_CERTS_DIR
import subprocess
from os import stat


class NfsExporter:
    Pyro4.config.SSL = True
    Pyro4.config.SSL_REQUIRECLIENTCERT = True  # 2-way ssl
    Pyro4.config.SSL_SERVERCERT = SSL_CERTS_DIR + "localhost.crt"
    Pyro4.config.SSL_SERVERKEY = SSL_CERTS_DIR + "localhost.key"
    Pyro4.config.SSL_CACERTS = SSL_CERTS_DIR + "rootCA.crt"  # to make ssl accept the self-signed master cert

    @Pyro4.expose
    def test(self):
        return "ok"

    @staticmethod
    def __nfs4_syntax(path, to):
        # get the enclosing folder of the project
        if path.find(".ove") > 0:
            path = path[:path.rfind("/")]
        # apply destination
        if to is None:
            path = "*:"+path
        else:
            path = to+":"+path
        return path

    @Pyro4.expose
    def export(self, path, to=None):
        folder_uid = str(stat(path).st_uid)
        folder_gid = str(stat(path).st_gid)
        path = self.__nfs4_syntax(path, to)
        print("exporting", path)
        if subprocess.run(['exportfs', path, '-o', 'rw,all_squash,anonuid=' + folder_uid + ',anongid=' + folder_gid],
                          stdout=subprocess.PIPE).returncode != 0:
            print("There was an error exporting", path, "- Worker node might not be able to access media.")

    @Pyro4.expose
    def unexport(self, path, to=None):
        path = self.__nfs4_syntax(path, to)
        print("unexporting", path)
        if subprocess.run(['exportfs', '-u', path], stdout=subprocess.PIPE).returncode != 0:
            print("There was an error unexporting", path, "- media might still be accessible.")

    def start(self):
        if subprocess.run(['systemctl', 'start', "nfs-server.service"], stdout=subprocess.PIPE).returncode != 0:
            print("There was an error starting nfs-server - make sure NFSv4 is installed.")

        if subprocess.run(['systemctl', 'restart', "rpcbind.service"], stdout=subprocess.PIPE).returncode != 0:
            print("There was an error restarting rpcbind - this might be an issue.")

        d = CertValidatingDaemon(port=9091)
        uri = d.register(self, "NfsExporter")
        print("NFS Exporter ready. URI:", uri)
        d.requestLoop()

    def stop(self):
        if subprocess.run(['systemctl', 'stop', "nfs-server.service"], stdout=subprocess.PIPE).returncode != 0:
            print("There was an error stopping nfs-server.")


if __name__ == '__main__':
    nfsExporter = NfsExporter()
    nfsExporter.start()
    nfsExporter.stop()
