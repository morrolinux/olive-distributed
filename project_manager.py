from xml.dom import minidom
import os


class Job:
    def __init__(self, job_path, job_weight):
        self.job_path = job_path
        self.job_weight = job_weight

    def __str__(self):
        return "" + self.job_path + " : " + str(self.job_weight)


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

    def get_job_complexity(self, j):
        olive_project = minidom.parse(j)
        items = olive_project.getElementsByTagName('clip')
        num_clips = len(items)
        return max(int(v.attributes['out'].value) for v in items[max(0, num_clips - 50):num_clips])

    def get_job(self, node_rank):
        if len(self.jobs) <= 0:
            return Job("-1", -1)

        max_score = max(node.cpu_score for node in self.render_nodes)
        min_score = min(node.cpu_score for node in self.render_nodes)
        max_weight = max(job.job_weight for job in self.jobs)
        min_weight = min(job.job_weight for job in self.jobs)
        print("max weight:", max_weight, "\nmin weight:", min_weight)

        tmp = Job("-1", -1)

        # TODO: improve classification
        if node_rank > (max_score + min_score)/2:
            for j in self.jobs:
                if j.job_weight >= (max_weight + min_weight)/2:
                    tmp = j
                    self.jobs.remove(j)
                    break
        else:
            for j in self.jobs:
                if j.job_weight <= (max_weight + min_weight)/2:
                    tmp = j
                    self.jobs.remove(j)
                    break

        return tmp
