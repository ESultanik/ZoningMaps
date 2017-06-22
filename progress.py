import sys
import time

class Progress(object):
    def __init__(self, time, percent):
        self.time = time
        self.percent = percent

def default_logger(msg):
    sys.stderr.write(msg)
    sys.stderr.flush()
        
class TimeEstimator(object):
    def __init__(self, logger = None, start_value = 0.0, end_value = 100.0, precision = 2, interval = 3.0, window = None):
        self.value = start_value
        self.end_value = end_value
        self.progress = []
        if logger is None:
            logger = default_logger
        self.logger = logger
        self.interval = interval
        self.precision = precision
        if window is None:
            window = interval * 4
        self.window = window
        self.last_log_time = 0
        self.last_percent = -1
        self.start_time = time.time()
    def get_time(self):
        return time.time()
    def increment(self, increment = 1):
        self.value += increment
        self.refresh()
    def update(self, new_value):
        self.value = new_value
        self.refresh()
    def force_next_refresh(self):
        self.last_percent = -1
    def refresh(self):
        raw_percent = float((self.value) * 10**(2+self.precision)) / float(self.end_value)
        percent = float(int(raw_percent)) / 10**self.precision
        raw_percent /= 10**self.precision
        current_time = time.time()
        self.progress.append(Progress(current_time, raw_percent))
        if percent > self.last_percent or not self.progress or current_time - self.last_log_time >= self.interval:
            self.last_log_time = current_time
            self.last_percent = percent
            prune_index = 0
            while len(self.progress) - prune_index > 2 and current_time - self.progress[prune_index].time > self.window:
                prune_index += 1
            self.progress = self.progress[prune_index:]
            if raw_percent == 0 or len(self.progress) < 2 or self.progress[-1].percent == self.progress[0].percent:
                time_remaining = "????"
            else:
                seconds_remaining = (current_time - self.progress[0].time) / (self.progress[-1].percent - self.progress[0].percent) * (100.0 - raw_percent)
                time_remaining = ""
                if seconds_remaining >= 60**2:
                    hours = int(seconds_remaining / 60**2)
                    time_remaining += "%d:" % hours
                    seconds_remaining -= hours * 60**2
                if seconds_remaining >= 60 or time_remaining:
                    minutes = int(seconds_remaining / 60)
                    time_remaining += "%02d:" % minutes
                    seconds_remaining -= minutes * 60
                if not time_remaining:
                    time_remaining = "%.2f seconds" % seconds_remaining
                else:
                    time_remaining += "%02d" % int(seconds_remaining)
            self.logger("\r%s\r%.2f%% %s remaining" % (' ' * 40, percent, time_remaining))
