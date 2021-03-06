import time
import Pyro4.core
import Pyro4.errors
import subprocess
from Pyro4.util import SerializerBase
from job import Job, ExportRange
from ssl_utils import CertCheckingProxy, LOCAL_HOSTNAME, SSL_CERTS_DIR, OD_FOLDER
from pathlib import Path
import os
import sys
import shutil
import threading
import signal


class WorkerNode:
    Pyro4.config.SSL = True
    Pyro4.config.SSL_CACERTS = OD_FOLDER + SSL_CERTS_DIR + "rootCA.crt"  # to make ssl accept the self-signed node cert
    Pyro4.config.SSL_CLIENTCERT = OD_FOLDER + SSL_CERTS_DIR + LOCAL_HOSTNAME + ".crt"
    Pyro4.config.SSL_CLIENTKEY = OD_FOLDER + SSL_CERTS_DIR + LOCAL_HOSTNAME + ".key"
    sys.excepthook = Pyro4.util.excepthook

    def __init__(self, address):
        self.TEMP_DIR = '/tmp/olive'
        self.address = address
        self.cpu_score = 0
        self.net_score = 0
        self._job_start_time = None
        self._job = None
        self.sample_weight = None
        self.sample_time = None
        self.worker_options = dict()
        self.olive_export_process = None
        self.terminating = False
        self.MASTER_ADDRESS = None
        self.MOUNTPOINT_DEFAULT = None
        self.job_dispatcher = None
        self.nfs_mounter = None

    def setup(self):
        signal.signal(signal.SIGINT, self.termination_handler)
        with open(OD_FOLDER + SSL_CERTS_DIR + 'whoismaster') as f:
            self.MASTER_ADDRESS = f.read().strip()
        self.MOUNTPOINT_DEFAULT = str(Path.home())+'/olive-share/'
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

    def termination_handler(self, signum, frame):
        print("stopping threads and clean termination...")
        self.terminating = True
        quit(0)

    def __connection_watchdog(self):
        while not self.terminating:
            time.sleep(5)
            try:
                self.job_dispatcher.test()
            except Pyro4.errors.CommunicationError:
                if self.olive_export_process is not None:
                    print("Lost connection to the master, aborting ongoing exports...")
                    self.olive_export_process.terminate()

    def run_benchmark(self):
        import random
        self.cpu_score = random.randrange(1, 10)
        self.net_score = random.randrange(1, 10)
        self.cpu_score = float(subprocess.run([OD_FOLDER + 'bench/bench-host.sh'], stdout=subprocess.PIPE).stdout)
        print("node", self.address, "\t\tCPU:", self.cpu_score)

    def run(self):
        if not Path(self.TEMP_DIR).exists():
            os.mkdir(self.TEMP_DIR)
        threading.Thread(target=self.__connection_watchdog).start()

        while not self.terminating:
            try:
                print(self.job_dispatcher.test())
            except Pyro4.errors.CommunicationError as e:
                print(e, "\nCan't connect to dispatcher, retrying...")
                time.sleep(1)
                continue

            if self.cpu_score is None or self.cpu_score == 0:
                self.run_benchmark()
            self.worker_options.update(self.job_dispatcher.get_worker_options())
            self.job_dispatcher.join_work(self)
            self.__run()
            time.sleep(1)

    def __run(self):
        while True:
            try:
                j, export_range = self.job_dispatcher.get_job(self)
            except Pyro4.errors.CommunicationError:
                return
            print("got job:", j, (export_range if export_range is not None else ""))
            if j.job_path == "abort":
                print(self.address, "\tterminating...")
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

        project_name = j.job_path[j.job_path.rfind("/") + 1:]
        olive_args = ['olive-editor', self.MOUNTPOINT_DEFAULT + project_name, '-e']

        if export_range is not None:
            #  Here we need to call deserialization manually because of dynamic typing
            #  ( not all implementations of dispatcher return (Job, ExportRange) )
            if isinstance(export_range, dict):
                export_range = ExportRange.export_range_dict_to_class("job.ExportRange", export_range)
            olive_args.append(str(export_range.instance_id))
            olive_args.append('--export-start')
            olive_args.append(str(export_range.start))
            olive_args.append('--export-end')
            olive_args.append(str(export_range.end))

        # Do the actual export with the given parameters
        os.chdir(self.TEMP_DIR)
        self.olive_export_process = subprocess.Popen(olive_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.olive_export_process.wait()
        if export_range is not None:
            export_name = export_range.instance_id + ".mp4"
        else:
            export_name = project_name + ".mp4"

        # Move the exported video to the NFS share
        try:
            shutil.move(export_name, self.MOUNTPOINT_DEFAULT)
            file_moved = True
        except OSError:
            file_moved = False

        # cleanup partial files
        for root, dirs, files in os.walk(self.TEMP_DIR):
            for file in files:
                os.remove(file)

        # dummy export jobs:
        # time.sleep((j.job_weight/self.cpu_score)/100)
        # time.sleep(1)
        # import random
        # if random.randrange(-100, 100) > 0:
        #     olive_export = subprocess.run(['true'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # success
        # else:
        #     olive_export = subprocess.run(['false'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)   # failure

        if self.olive_export_process.returncode == 0 and file_moved:
            print("Job done:", j.job_path, (export_range.number if export_range is not None else ""))
        else:
            print("Error exporting", j.job_path, (export_range.number if export_range is not None else ""))

        return_code = int(self.olive_export_process.returncode or not file_moved)
        self.olive_export_process = None

        # If we completed a with a full job, umount. Otherwise umount on abort
        if not j.split:
            self.nfs_mounter.umount(self.MOUNTPOINT_DEFAULT)

        try:
            self.job_dispatcher.report(self, j, return_code, export_range)
        except Pyro4.errors.ConnectionClosedError:
            return
        except Pyro4.errors.CommunicationError:
            return
        except ConnectionRefusedError:
            return

        self.sample_weight = j.job_weight
        self.sample_time = time.time() - self._job_start_time
        self._job = None

    @staticmethod
    def node_dict_to_class(classname, d):
        r = WorkerNode(d["address"])
        r.cpu_score = d["cpu_score"]
        r.net_score = d["net_score"]
        r._job_start_time = d["_job_start_time"]
        r.sample_weight = d["sample_weight"]
        r.sample_time = d["sample_time"]
        return r
