# run python node_service.py on every render node!
import Pyro4
import time

@Pyro4.expose
class NodeService(object):
    def __init__(self):
        pass

    def run_benchmark(self):
        import random
        cpu_score = random.randrange(1, 10)
        net_score = random.randrange(1, 10)
        # self.cpu_score = float(os.popen("./bench-host.sh morro " + str(self.address)).read())
        score = cpu_score  # + net_score
        return score

    def run_job(self, job_path, name, start, end, wait=0):
        job_start = job_end = job_name = ""
        if start is not None:
            job_start = " "+str(start)
        if end is not None:
            job_end = " "+str(end)
        if name is not None:
            job_name = " "+str(name)

        time.sleep(wait)
        # os.system("./render-on-host.sh \"" + job_path + "\" morro " +
        #           str(self.address) + job_name + job_start + job_end)



Pyro4.Daemon.serveSimple({
    NodeService: 'NodeService',
}, host="0.0.0.0", port=9090, ns=False, verbose=True)
