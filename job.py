import random


class Job:
    def __init__(self, job_path, job_weight, split=False):
        self.job_path = job_path
        self.job_weight = job_weight
        self.len = job_weight
        self.split = split

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
        return j


class ExportRange:
    def __init__(self, number, start, end, instance_id=None):
        self.number = number
        self.start = start
        self.end = end
        self.instance_id = instance_id
        if instance_id is None:
            self.reset_instance()

    def reset_instance(self):
        self.new_instance(-1)

    def new_instance(self, instance_id=None):
        if instance_id is None:
            self.instance_id = random.randint(1, 99999999)
        else:
            self.instance_id = instance_id

    @staticmethod
    def export_range_dict_to_class(classname, d):
        er = ExportRange(d["number"], d["start"], d["end"], d["instance_id"])
        return er

    @staticmethod
    def export_range_class_to_dict(obj):
        return {
            "number": obj.number,
            "start": obj.start,
            "end": obj.end,
            "instance_id": obj.instance_id
        }

    def __str__(self):
        return str(self.number) + " | (len: " + str(self.end - self.start) + ") | " + str(self.instance_id)

    def __hash__(self):
        return hash(self.number)

    def __eq__(self, other):
        return self.number == other.number

    def __lt__(self, other):
        return self.number < other.number

    def __le__(self, other):
        return self.number <= other.number

    def __ne__(self, other):
        return self.number != other.number

    def __gt__(self, other):
        return self.number > other.number

    def __ge__(self, other):
        return self.number >= other.number


abort_job = Job("abort", -1)
