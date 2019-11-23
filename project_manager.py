from xml.dom import minidom
import os


class Job:
    def __init__(self, job_path, job_weight):
        self.job_path = job_path
        self.job_weight = job_weight

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

    def get_job_complexity(self, j):
        olive_project = minidom.parse(j)
        items = olive_project.getElementsByTagName('clip')
        num_clips = len(items)
        return max(int(v.attributes['out'].value) for v in items[max(0, num_clips - 50):num_clips])

    def get_job(self, node_rank):
        # print("job request from", node_rank)
        if len(self.jobs) <= 0:
            return Job("-1", -1)

        max_score = max(node.cpu_score for node in self.render_nodes)
        min_score = min(node.cpu_score for node in self.render_nodes)
        max_weight = max(job.job_weight for job in self.jobs)
        min_weight = min(job.job_weight for job in self.jobs)
        # print("max weight:", max_weight, "\nmin weight:", min_weight)

        tmp = Job("-1", -1)
        fuzzy_job = 0

        if max_score != min_score:
            fuzzy_job = min_weight + ((max_weight - min_weight) / (max_score - min_score)) * (node_rank - min_score)

        assigned_job_weight = min(self.jobs, key=lambda x: abs(x.job_weight - fuzzy_job))

        for j in self.jobs:
            if j == assigned_job_weight:
                tmp = j
                self.jobs.remove(j)
                break

        return tmp
