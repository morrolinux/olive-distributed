from xml.dom import minidom
import os


class Job:
    def __init__(self, job_path, job_weight):
        self.job_path = job_path
        self.job_weight = job_weight

    def __str__(self):
        return "" + self.job_path + " : " + str(self.job_weight)


class ProjectManager:
    def __init__(self):
        self.jobs = []

    def explore(self, folder):
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.endswith(".ove"):
                    job_path = os.path.join(root, file)
                    self.jobs.append(Job(job_path, self.get_job_complexity(job_path)))
        return self.jobs

    def get_job_complexity(self, j):
        olive_project = minidom.parse(j)
        items = olive_project.getElementsByTagName('clip')
        num_clips = len(items)
        return max(int(v.attributes['out'].value) for v in items[max(0, num_clips - 50):num_clips])
