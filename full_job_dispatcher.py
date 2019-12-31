import Pyro4.core
from job_dispatcher import JobDispatcher
from job import Job, abort_job


class FullJobDispatcher(JobDispatcher):
    def __init__(self):
        super().__init__()
        self.jobs = None

    @Pyro4.expose
    def report(self, node, job, exit_status, export_range=None):
        print("NODE", node.address, "completed job", job.job_path, "with status", exit_status)
        # If the export fails, re-insert it in the job queue
        if exit_status != 0:
            self.jobs.append(job)

        # In any case, always remove the share after a worker is done
        self.nfs_exporter.unexport(job.job_path, to=node.address)

    @Pyro4.expose
    def get_job(self, n):
        if len(self.jobs) <= 0:
            print("PROJECT MANAGER: no more work to do")
            return abort_job, None, None, None

        if self.first_run:
            import time
            print("waiting to see if any other workers are joining us...")
            time.sleep(5)
            self.first_run = False

        # Assign a job based on node benchmark score
        max_score = max(node.cpu_score for node in self.workers)
        min_score = min(node.cpu_score for node in self.workers)
        max_weight = max(job.job_weight for job in self.jobs)
        min_weight = min(job.job_weight for job in self.jobs)
        fuzzy_job_weight = 0

        if max_score != min_score:
            fuzzy_job_weight = min_weight + ((max_weight - min_weight) / (max_score - min_score)) * (n.cpu_score - min_score)

        assigned_job = min(self.jobs, key=lambda x: abs(x.job_weight - fuzzy_job_weight))

        if assigned_job is None:
            return abort_job, None, None, None

        # Slow tail fix:
        # if there are more nodes than jobs, check weather a faster node is about to finish its work before assignment
        # if so, don't assign the current job to the current (slower) node and terminate it.
        # TODO: with Pyro, workers in self.render nodes are not updated from remote and cannot provide useful ETA
        if len(self.jobs) < len(self.workers):
            for worker in self.workers:
                w_eta = worker.job_eta() + worker.job_eta(assigned_job)
                n_eta = n.job_eta(assigned_job)
                if w_eta < n_eta:
                    return abort_job, None, None, None

        # Export the folder via NFS so that the worker node can access it
        self.nfs_exporter.export(assigned_job.job_path, to=n.address)

        print(n.address + "\trunning job: ", assigned_job.job_path[assigned_job.job_path.rfind("/")+1:],
              "\tWeight: ", assigned_job.job_weight)
        self.jobs.remove(assigned_job)
        return assigned_job, None, None, None
