class Job:
    def __init__(self, job_path, job_weight, split=False):
        self.job_path = job_path
        self.job_weight = job_weight
        self.len = job_weight
        self.split = split
        self.last_assigned_frame = 0
        self.parts = 0
        self.failed_ranges = set()
        self.completed_ranges = set()

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

    def fail(self, export_range):
        self.failed_ranges.add(export_range)

    def complete(self, export_range):
        self.completed_ranges.add(export_range)
        try:
            self.failed_ranges.remove(export_range)
        except KeyError:
            pass

    def split_job_finished(self):
        if len(self.completed_ranges) == 0:
            total_len_covered = False
        else:
            total_len_covered = self.len == max(n.end for n in self.completed_ranges)
        all_parts_done = self.parts == len(self.completed_ranges)
        no_failed_ranges = len(self.failed_ranges) == 0
        return total_len_covered and all_parts_done and no_failed_ranges

    @staticmethod
    def job_dict_to_class(classname, d):
        print("job_dict_to_class")
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
        print("export_range_dict_to_class")
        er = ExportRange(d["name"], d["start"], d["end"])
        return er

    @staticmethod
    def export_range_class_to_dict(obj):
        print("export_range_class_to_dict")
        return {
            "name": obj.name,
            "start": obj.start,
            "end": obj.end
        }

    def __str__(self):
        return str(self.name) + " : " + str(self.start) + " - " + str(self.end)


abort_job = Job("abort", -1)
