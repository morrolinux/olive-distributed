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
    def __init__(self, name, start, end, instance_id):
        self.name = name
        self.start = start
        self.end = end
        self.instance_id = instance_id

    @staticmethod
    def export_range_dict_to_class(classname, d):
        er = ExportRange(d["name"], d["start"], d["end"], d["instance_id"])
        return er

    @staticmethod
    def export_range_class_to_dict(obj):
        return {
            "name": obj.name,
            "start": obj.start,
            "end": obj.end,
            "instance_id": obj.instance_id
        }

    def __str__(self):
        return str(self.name) + " : {" + str(self.start) + " - " + str(self.end) + \
               "} | (" + str(self.end - self.start) + " frames)"

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return self.name == other.name

    def __lt__(self, other):
        return self.name < other.name

    def __le__(self, other):
        return self.name <= other.name

    def __ne__(self, other):
        return self.name != other.name

    def __gt__(self, other):
        return self.name > other.name

    def __ge__(self, other):
        return self.name >= other.name


abort_job = Job("abort", -1)
