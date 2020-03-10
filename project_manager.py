from xml.dom import minidom
import os
from job import Job
import subprocess


class ProjectManager:
    def __init__(self):
        self.jobs = []

    def explore(self, folder):
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.endswith(".ove"):
                    job_path = os.path.join(root, file)
                    print("adding project:", job_path)
                    self.add_project(job_path)

    def add_project(self, project, part=False):
        self.jobs.append(Job(project, self.get_job_complexity(project), split=part))

    def add_video(self, video):
        self.jobs.append(Job(video, self.get_video_len(video), split=True))

    @staticmethod
    def get_job_complexity(j):
        olive_project = minidom.parse(j)
        items = olive_project.getElementsByTagName('clip')
        num_clips = len(items)
        return max(int(v.attributes['out'].value) for v in items[max(0, num_clips - 50):num_clips])

    @staticmethod
    def get_video_len(v):
        ffprobe_params = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=duration',
                          '-of', 'default=noprint_wrappers=1:nokey=1', v]
        return float(subprocess.run(ffprobe_params, stdout=subprocess.PIPE).stdout)
