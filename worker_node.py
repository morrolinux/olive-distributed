import time
import Pyro4.core
import Pyro4.errors
import subprocess
from Pyro4.util import SerializerBase
from job import Job
from ssl_utils import CertCheckingProxy, LOCAL_HOSTNAME, SSL_CERTS_DIR
from pathlib import Path
import os


class WorkerNode:
    Pyro4.config.SSL = True
    Pyro4.config.SSL_CACERTS = SSL_CERTS_DIR + "rootCA.crt"  # to make ssl accept the self-signed node cert
    Pyro4.config.SSL_CLIENTCERT = SSL_CERTS_DIR + LOCAL_HOSTNAME + ".crt"
    Pyro4.config.SSL_CLIENTKEY = SSL_CERTS_DIR + LOCAL_HOSTNAME + ".key"

    def __init__(self, address):
        with open(SSL_CERTS_DIR + 'whoismaster') as f:
            self.MASTER_ADDRESS = f.read().strip()
        self.MOUNTPOINT_DEFAULT = str(Path.home())+'/olive-share'
        self.address = address
        self.cpu_score = 0
        self.net_score = 0
        self._job_start_time = None
        self._job = None
        self.sample_weight = None
        self.sample_time = None
        self.job_dispatcher = CertCheckingProxy('PYRO:JobDispatcher@' + self.MASTER_ADDRESS + ':9090')
        self.nfs_mounter = CertCheckingProxy('PYRO:NfsMounter@' + 'localhost' + ':9092')
        SerializerBase.register_dict_to_class("job.Job", Job.job_dict_to_class)

    def job_eta(self, j=None):
        if self.sample_time is None or self.sample_weight is None:
            return 9223372036854775807

        if j is not None:
            t = (j.job_weight * self.sample_time) / self.sample_weight
        elif self._job is not None:
            t = self.job_eta(self._job) - (time.time() - self._job_start_time)
        else:
            t = 0
        return t

    def run_benchmark(self):
        import random
        self.cpu_score = random.randrange(1, 10)
        self.net_score = random.randrange(1, 10)
        self.cpu_score = float(subprocess.run(['bench/bench-host.sh'], stdout=subprocess.PIPE).stdout)
        print("node", self.address, "\t\tCPU:", self.cpu_score)

    def run(self):
        while True:
            try:
                print(self.job_dispatcher.test())
            except Pyro4.errors.CommunicationError as e:
                print(e, "\nCan't connect to dispatcher, retrying...")
                time.sleep(1)
                continue

            self.run_benchmark()
            self.job_dispatcher.join_work(self)
            self.__run()
            return

    def __run(self):
        while True:
            j, name, start, end = self.job_dispatcher.get_job(self)
            print("got job:", j)
            if j.job_path == "abort":
                print(self.address, "\tterminating...")
                return
            if j.job_path == "retry":
                time.sleep(j.job_weight)
                continue
            # mount the NFS share before starting
            if self.nfs_mounter.mount(j.job_path, self.MASTER_ADDRESS, self.MOUNTPOINT_DEFAULT) != 0:
                self.job_dispatcher.report(self, j, -1)
                return
            self.run_job(j, name, start, end)

    def run_job(self, j, name, start, end):
        self._job_start_time = time.time()
        self._job = j

        project_path = j.job_path[j.job_path.rfind("/") + 1:]
        olive_args = ['olive-editor', project_path, '-e']

        job_name = ": "
        if name is not None:
            olive_args.append(str(name))
            job_name = job_name + str(name)
        if start is not None:
            olive_args.append('--export-start')
            olive_args.append(str(start))
        if end is not None:
            olive_args.append('--export-end')
            olive_args.append(str(end))

        initial_folder = os.getcwd()
        os.chdir(self.MOUNTPOINT_DEFAULT)
        olive_export = subprocess.run(olive_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        os.chdir(initial_folder)
        # dummy export jobs:
        # time.sleep((j.job_weight/self.cpu_score)/100)
        # olive_export = subprocess.run(['true'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # success
        # olive_export = subprocess.run(['false'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)   # failure

        if olive_export.returncode == 0:
            print("Exported successfully:", j.job_path, job_name)
        else:
            print("Error exporting", j.job_path, "\n", olive_export.stdout, olive_export.stderr)

        self.nfs_mounter.umount(self.MOUNTPOINT_DEFAULT)
        self.job_dispatcher.report(self, j, olive_export.returncode)

        self.sample_weight = j.job_weight
        self.sample_time = time.time() - self._job_start_time
        self._job = None

    @staticmethod
    def node_dict_to_class(classname, d):
        # print("{deserializer hook, converting to class: %s}" % d)
        r = WorkerNode(d["address"])
        r.cpu_score = d["cpu_score"]
        r.net_score = d["net_score"]
        r._job_start_time = d["_job_start_time"]
        r.sample_weight = d["sample_weight"]
        r.sample_time = d["sample_time"]
        return r
