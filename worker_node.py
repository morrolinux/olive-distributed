import time
import Pyro4.core
import Pyro4.errors
import subprocess
from Pyro4.util import SerializerBase
from job import Job, ExportRange
from ssl_utils import CertCheckingProxy, LOCAL_HOSTNAME, SSL_CERTS_DIR
from pathlib import Path
import os
import sys


class WorkerNode:
    Pyro4.config.SSL = True
    Pyro4.config.SSL_CACERTS = SSL_CERTS_DIR + "rootCA.crt"  # to make ssl accept the self-signed node cert
    Pyro4.config.SSL_CLIENTCERT = SSL_CERTS_DIR + LOCAL_HOSTNAME + ".crt"
    Pyro4.config.SSL_CLIENTKEY = SSL_CERTS_DIR + LOCAL_HOSTNAME + ".key"
    sys.excepthook = Pyro4.util.excepthook

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
        self.worker_options = dict()
        self.job_dispatcher = CertCheckingProxy('PYRO:JobDispatcher@' + self.MASTER_ADDRESS + ':9090')
        self.nfs_mounter = CertCheckingProxy('PYRO:NfsMounter@' + 'localhost' + ':9092')
        SerializerBase.register_dict_to_class("job.ExportRange", ExportRange.export_range_dict_to_class)
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
            self.worker_options.update(self.job_dispatcher.get_worker_options())
            self.job_dispatcher.join_work(self)
            self.__run()
            return

    def __run(self):
        while True:
            j, export_range = self.job_dispatcher.get_job(self)
            print("got job:", j)
            if j.job_path == "abort":
                print(self.address, "\tterminating...")
                # In any case umount when finished
                self.nfs_mounter.umount(self.MOUNTPOINT_DEFAULT)
                return
            if j.job_path == "retry":
                time.sleep(j.job_weight)
                continue
            # mount the NFS share before starting
            if self.nfs_mounter.mount(j.job_path, self.MASTER_ADDRESS, self.MOUNTPOINT_DEFAULT,
                                      self.worker_options["nfs_tuning"]) != 0:
                self.job_dispatcher.report(self, j, -1, export_range)
                return
            self.run_job(j, export_range)

    def run_job(self, j, export_range):
        self._job_start_time = time.time()
        self._job = j

        project_path = j.job_path[j.job_path.rfind("/") + 1:]
        olive_args = ['olive-editor', project_path, '-e']

        if export_range is not None:
            # TODO: This is a bit ugly. Fix if possible.
            #  Here we need to call deserialization manually because of dynamic typing (not all implementations
            #  of dispatcher return Job, ExportRange)
            if isinstance(export_range, dict):
                export_range = ExportRange.export_range_dict_to_class("job.ExportRange", export_range)
            export_range.new_instance()
            olive_args.append(str(export_range.instance_id))
            olive_args.append('--export-start')
            olive_args.append(str(export_range.start))
            olive_args.append('--export-end')
            olive_args.append(str(export_range.end))

        initial_folder = os.getcwd()
        os.chdir(self.MOUNTPOINT_DEFAULT)
        olive_export = subprocess.run(olive_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        os.chdir(initial_folder)
        # dummy export jobs:
        # time.sleep((j.job_weight/self.cpu_score)/100)
        # time.sleep(1)
        # import random
        # if random.randrange(-100, 100) > 0:
        #     olive_export = subprocess.run(['true'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # success
        # else:
        #     olive_export = subprocess.run(['false'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)   # failure

        if olive_export.returncode == 0:
            print("Exported successfully:", j.job_path, export_range.name)
        else:
            print("Error exporting", j.job_path, "\n", olive_export.stdout, olive_export.stderr)

        # If we completed a with a full job, umount. Otherwise umount on abort
        if not j.split:
            self.nfs_mounter.umount(self.MOUNTPOINT_DEFAULT)

        self.job_dispatcher.report(self, j, olive_export.returncode, export_range)

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
