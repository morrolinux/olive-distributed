from xml.dom import minidom
import os
import math
import threading
from job import Job
from job_dispatcher import JobDispatcher
import threading


class ProjectManager:
    def __init__(self):
        self.jobs = []

    def explore(self, folder):
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.endswith(".ove"):
                    job_path = os.path.join(root, file)
                    print("adding project:", job_path)
                    self.add(job_path)

    def add(self, project, part=False):
        self.jobs.append(Job(project, self.get_job_complexity(project), split=part))

    def get_job_complexity(self, j):
        olive_project = minidom.parse(j)
        items = olive_project.getElementsByTagName('clip')
        num_clips = len(items)
        return max(int(v.attributes['out'].value) for v in items[max(0, num_clips - 50):num_clips])
