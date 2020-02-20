class Job:
    def __init__(self, job_path, job_weight, split=False):
        self.job_path = job_path
        self.job_weight = job_weight
        self.len = job_weight
        self.split = split
        self.last_assigned_frame = 0
        self.parts = 0

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

    @staticmethod
    def job_dict_to_class(classname, d):
        j = Job(d["job_path"], d["job_weight"])
        j.len = d["len"]
        j.split = d["split"]
        j.last_assigned_frame = d["last_assigned_frame"]
        return j


class ExportRange:
    def __init__(self, name, start, end):
        self.name = name
        self.start = start
        self.end = end

    @staticmethod
    def export_range_dict_to_class(classname, d):
        er = ExportRange(d["name"], d["start"], d["end"])
        return er

    @staticmethod
    def export_range_class_to_dict(obj):
        return {
            "name": obj.name,
            "start": obj.start,
            "end": obj.end
        }

    def __str__(self):
        return str(self.name) + " : " + str(self.start) + " - " + str(self.end)


abort_job = Job("abort", -1)
