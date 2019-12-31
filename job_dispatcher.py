import Pyro4.core
from worker_node import WorkerNode
from Pyro4.util import SerializerBase
from ssl_utils import CertCheckingProxy, CertValidatingDaemon
from ssl_utils import LOCAL_HOSTNAME, SSL_CERTS_DIR
from global_settings import settings


class JobDispatcher:
    Pyro4.config.SSL = True
    Pyro4.config.SSL_REQUIRECLIENTCERT = True  # 2-way ssl
    Pyro4.config.SSL_SERVERCERT = SSL_CERTS_DIR + LOCAL_HOSTNAME + ".crt"
    Pyro4.config.SSL_SERVERKEY = SSL_CERTS_DIR + LOCAL_HOSTNAME + ".key"
    Pyro4.config.SSL_CACERTS = SSL_CERTS_DIR + "rootCA.crt"  # to make ssl accept the self-signed master cert

    # For using NFS mounter as a client
    Pyro4.config.SSL_CLIENTCERT = Pyro4.config.SSL_SERVERCERT
    Pyro4.config.SSL_CLIENTKEY = Pyro4.config.SSL_SERVERKEY

    def __init__(self):
        self.daemon = None
        self.workers = []
        SerializerBase.register_dict_to_class("worker_node.WorkerNode", WorkerNode.node_dict_to_class)
        self.nfs_exporter = CertCheckingProxy('PYRO:NfsExporter@localhost:9091')
        self.first_run = True

    @Pyro4.expose
    def test(self):
        return "connection ok"

    @Pyro4.expose
    def get_worker_options(self):
        # options = {"nfs_tuning": ['-o', 'noacl,nocto,noatime,nodiratime']}
        options = {"nfs_tuning": ['-o', 'async']}
        return options

    @Pyro4.expose
    def join_work(self, node):
        self.workers.append(node)

    @Pyro4.expose
    def report(self, node, job, exit_status, export_range=None):
        pass

    @Pyro4.expose
    def get_job(self, n):
        pass

    def start(self):
        print("selected workflow:", settings.dispatcher["workflow"])
        try:
            self.nfs_exporter.test()
        except Pyro4.errors.CommunicationError as e:
            print("Can't connect to local NFS exporter service, make sure it's running.\n", e)
            return

        self.daemon = CertValidatingDaemon(host=LOCAL_HOSTNAME, port=9090)
        test_uri = self.daemon.register(self, "JobDispatcher")
        print("Job dispatcher ready. URI:", test_uri)
        self.daemon.requestLoop()

