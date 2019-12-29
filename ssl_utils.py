import Pyro4.core
import socket
import os

# Doesn't work consistently
# LOCAL_HOSTNAME = socket.gethostbyname_ex(socket.gethostname())[0]


# Works consistently
def fqdn():
    full = os.popen('echo -n $(host -TtA $(hostname -s)|grep \"has address\"|awk \'{print $1}\') ; '
                          'if [[ \"${fqn}\" == \"\" ]] ; then fqn=$(hostname -s) ; fi').read()
    domain = full[full.find('.'):]
    return socket.gethostname() + domain


LOCAL_HOSTNAME = fqdn()
SSL_CERTS_DIR = "ssl/certs/"


class CertCheckingProxy(Pyro4.core.Proxy):
    @staticmethod
    def verify_cert(cert):
        if not cert:
            raise Pyro4.errors.CommunicationError("cert missing")

    def _pyroValidateHandshake(self, response):
        cert = self._pyroConnection.getpeercert()
        self.verify_cert(cert)


class CertValidatingDaemon(Pyro4.core.Daemon):
    def validateHandshake(self, conn, data):
        cert = conn.getpeercert()
        if not cert:
            raise Pyro4.errors.CommunicationError("node cert missing")
        return super(CertValidatingDaemon, self).validateHandshake(conn, data)
