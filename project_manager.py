from xml.dom import minidom
import os
import math


class Job:
    def __init__(self, job_path, job_weight, split=False):
        self.job_path = job_path
        self.job_weight = job_weight
        self.len = job_weight
        self.split = split
        self.last_frame = 0

    def __str__(self):
        return "" + self.job_path + " : " + str(self.job_weight)

    def __eq__(self, other):
        return self.job_weight == other.job_weight

    def __lt__(self, other):
        return self.job_weight < other.job_weight

    def __le__(self, other):
        return self.job_weight <= other.job_weight

    def __ne__(self, other):
        return self.job_weight != other.job_weight

    def __gt__(self, other):
        return self.job_weight > other.job_weight

    def __ge__(self, other):
        return self.job_weight >= other.job_weight


class ProjectManager:
    def __init__(self, render_nodes):
        self.jobs = []
        self.render_nodes = render_nodes

    def explore(self, folder):
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.endswith(".ove"):
                    job_path = os.path.join(root, file)
                    self.jobs.append(Job(job_path, self.get_job_complexity(job_path)))

    def add(self, project, part=False):
        self.jobs.append(Job(project, self.get_job_complexity(project), split=part))

    def get_job_complexity(self, j):
        olive_project = minidom.parse(j)
        items = olive_project.getElementsByTagName('clip')
        num_clips = len(items)
        return max(int(v.attributes['out'].value) for v in items[max(0, num_clips - 50):num_clips])

    def get_job(self, n):
        if len(self.jobs) <= 0:
            print("PROJECT MANAGER: no more work to do")
            return Job("abort", -1), None, None

        max_score = max(node.cpu_score for node in self.render_nodes)
        min_score = min(node.cpu_score for node in self.render_nodes)
        max_weight = max(job.job_weight for job in self.jobs)
        min_weight = min(job.job_weight for job in self.jobs)

        abort = Job("-1", -1)
        fuzzy_job_weight = 0

        if max_score != min_score:
            fuzzy_job_weight = min_weight + ((max_weight - min_weight) / (max_score - min_score)) * (n.cpu_score - min_score)

        assigned_job = min(self.jobs, key=lambda x: abs(x.job_weight - fuzzy_job_weight))

        if assigned_job is None:
            return abort, None, None

        # if there are more nodes than jobs, check weather a faster node is about to finish its work before assignment
        # if so, don't assign the current job to the current (slower) node and terminate it.
        if len(self.jobs) < len(self.render_nodes) and not assigned_job.split:
            for worker in self.render_nodes:
                w_eta = worker.job_eta() + worker.job_eta(assigned_job)
                n_eta = n.job_eta(assigned_job)
                if w_eta < n_eta:
                    '''
                    print("PROJECT MANAGER: job", assigned_job, "\n",
                          n.address, "ETA:", round(n.job_eta(assigned_job)), "\t",
                          worker.address, "ETA:", round(w_eta), "\n",
                          "Refusing to assign a job to", n.address)
                    '''
                    return Job("abort", -1), None, None

        if assigned_job.split:
            tot_w = 0
            for worker in self.render_nodes:
                tot_w = tot_w + worker.cpu_score
            chunk_size = math.ceil((n.cpu_score / tot_w) * assigned_job.len)
            job_start = assigned_job.last_frame
            job_end = min(job_start + chunk_size, assigned_job.len)
            assigned_job.last_frame = job_end
            print(n.address, "will export", assigned_job.job_path, "from", job_start, "to", job_end)
            if assigned_job.len == job_end:
                self.jobs.remove(assigned_job)
                # TODO: assegnare un nome sequenziale ai progetti da esportare per poterli mergiare con ffmpeg
                # TODO: quando ciascun nodo che ha preso parte ad un job split chiede un nuovo lavoro, so di aver
                #  terminato e posso ripulire dall'archivio .tar e UNIRE i file parziali ritornati dai nodi
            return assigned_job, job_start, job_end

        self.jobs.remove(assigned_job)
        return assigned_job, None, None
