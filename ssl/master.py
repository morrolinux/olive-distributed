from __future__ import print_function
import sys
import Pyro4.core
import Pyro4.errors

if sys.version_info < (3, 0):
    input = raw_input


Pyro4.config.SSL = True
Pyro4.config.SSL_CACERTS = "certs/node_cert.pem"    # to make ssl accept the self-signed node cert
Pyro4.config.SSL_CLIENTCERT = "certs/master_cert.pem"
Pyro4.config.SSL_CLIENTKEY = "certs/master_key.pem"
print("SSL enabled (2-way).")


def verify_cert(cert):
    if not cert:
        raise Pyro4.errors.CommunicationError("cert missing")
    '''
    if cert["serialNumber"] != "D163AB82B8B74DE6":
        raise Pyro4.errors.CommunicationError("cert serial number incorrect")
    issuer = dict(p[0] for p in cert["issuer"])
    subject = dict(p[0] for p in cert["subject"])
    if issuer["organizationName"] != "Razorvine.net":
        # issuer is not often relevant I guess, but just to show that you have the data
        raise Pyro4.errors.CommunicationError("cert not issued by Razorvine.net")
    if subject["countryName"] != "NL":
        raise Pyro4.errors.CommunicationError("cert not for country NL")
    if subject["organizationName"] != "Razorvine.net":
        raise Pyro4.errors.CommunicationError("cert not for Razorvine.net")
    print("(SSL server cert is ok: serial={ser}, subject={subj})"
          .format(ser=cert["serialNumber"], subj=subject["organizationName"]))
    '''


# to make Pyro verify the certificate on new connections, use the handshake mechanism:
class CertCheckingProxy(Pyro4.core.Proxy):
    def _pyroValidateHandshake(self, response):
        cert = self._pyroConnection.getpeercert()
        verify_cert(cert)


node_service_name = ('PYRO:NodeService@' + "localhost" + ':9090')
# node_service = Pyro4.core.Proxy(node_service_name)
print("node_service: ", node_service_name)

with CertCheckingProxy(node_service_name) as p:
    response = p.echo("client speaking")
    print("response:", response)
