import Pyro4.core


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
