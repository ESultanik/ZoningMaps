import bisect
import json
import progress
import zoning

def calculate_stream_size(stream):
    old_pos = stream.tell()
    stream.seek(0, 2)
    size = f.tell()
    stream.seek(old_pos, 0)
    return size

class NullFeatures(object):
    def __init__(self, map1_len, map2_len):
        self._mapping = map1_len * map2_len
        self._max_mapping = self._mapping * map1_len + 1
        self.regions = []
    def add_null_region(self, fromn, fromi, ton, toi):
        fromid = fromn * self._mapping + fromi
        toid = ton * self._mapping + toi
        bisect.insort_right(self.regions, (fromid, toid))
    def is_null(self, n, i):
        fid = n * self._mapping + i
        j = bisect.bisect_right(self.regions, (fid, self._max_mapping))
        if j == 0:
            return False
        else:
            return self.regions[j - 1][1] >= fid

def load_save_file(stream, logger = None):
    if hasattr(stream, "name"):
        estimator = progress.TimeEstimator(logger, 0, calculate_stream_size(stream), precision = 1)
    else:
        estimator = None
    save = {}
    map1_len = None
    map2_len = None
    null_features = None
    for line in stream:
        estimator.increment(len(line))
        data = json.loads(line)
        if map1_len is None:
            map1_len = data["MAP1_LEN"]
            map2_len = data["MAP2_LEN"]
            save[None] = null_features = NullFeatures(map1_len, map2_len)
            continue;
        elif data[0] is None:
            fromn, fromi = data[1]
            ton, toi = data[2]
            null_features.add_null_region(fromn, fromi, ton, toi)
            #for n in range(fromn, ton + 1):
            #    for i in range(fromi, map2_len):
            #        if n == ton and i == toi:
            #            break
            #        save[(n, i)] = None
        elif data[2] is None:
            save[(data[0], data[1])] = None
        else:
            features = []
            for f in data[2:]:
                if f is None:
                    features.append(None)
                else:
                    features.append(zoning.parse_feature(f))
            save[(data[0], data[1])] = features
    return save

class StateSaver(object):
    def __init__(self, save_state_to, flush_interval = 50000):
        self.stream = save_state_to
        self.flush_interval = flush_interval
        self.current_state_flush = 0
        self.last_state_flush = 0
        self.nulls_start = None
    def record_map_sizes(self, map1_len, map2_len):
        if self.stream is not None:
            self.stream.write("%s\n" % json.dumps({"MAP1_LEN" : map1_len, "MAP2_LEN" : map2_len}))
    def record(self, n, i, *args):
        if self.stream is None:
            return
        self.current_state_flush += 1
        flush = (self.current_state_flush - self.last_state_flush) >= self.flush_interval
        if args:
            if self.nulls_start:
                line = "[null,[%d,%d],[%d,%d]]" % (self.nulls_start[0], self.nulls_start[1], n, i)
                self.stream.write("%s\n" % line)
                flush = True
                self.nulls_start = None
            a = []
            for arg in args:
                if arg is None:
                    a.append(None)
                else:
                    a.append(arg.to_geo())
            line = json.dumps([n, i] + a)
            self.stream.write("%s\n" % line)
        else:
            if self.nulls_start is None:
                self.nulls_start = [n, i]
            #line = json.dumps([n, i, None])
        if flush:
            self.last_state_flush = self.current_state_flush
            self.stream.flush()

def intersect(map1, map2, logger = None, previous_save = None, save_state_to = None, incremental_save_path = None, incremental_save_time = 600):
    if logger is None:
        logger = lambda m : None
    map1 = zoning.ModifiableMap(map1)
    map2 = zoning.ModifiableMap(map2)
    estimator = progress.TimeEstimator(logger, 0, len(map1) * len(map2), precision = 2, interval = 3.0)
    saver = StateSaver(save_state_to)
    last_incremental_save = 0
    if previous_save is not None:
        logger("\r%s\rFast-forwarding using saved state..." % (' ' * 40))
    else:
        saver.record_map_sizes(len(map1), len(map2))
    for n, f1 in enumerate(map1):
        if f1.geometry.is_empty:
            continue
        for i, f2 in enumerate(map2):
            if previous_save is not None:
                if (n, i) in previous_save:
                    state = previous_save[(n,i)]
                    if state is None:
                        continue
                    map2[i] = state[0]
                    if state[1] is not None:
                        map2.append(state[1])
                        estimator.end_value = len(map1) * len(map2)
                    map1[n] = state[2]
                    if map1[n].geometry.is_empty:
                        break
                    continue
                elif previous_save[None].is_null(n, i):
                    continue
            estimator.update(n * len(map2) + i)
            if f2.geometry.is_empty:
                saver.record(n, i)
                continue
            try:
                isect = f1.geometry.intersection(f2.geometry)
            except Exception as e:
                logger("\r%s\rError: %s\n" % (' ' * 40, e))
                estimator.force_next_refresh()
                continue
            if isect.is_empty:
                saver.record(n, i)
                continue
            area_delta = 10.0 # square meters
            new_feature = zoning.ZoningFeature("%s->%s" % (f1.objectid, f2.objectid), f2.zoning, isect, f2.old_zoning + f1.zoning)
            new_state = [None, None, None]
            if new_feature.area() < area_delta:
                # The intersection is less than area_delta square meters, so it's probably just floating point error.
                # Skip it!
                saver.record(n, i)
                continue
            elif f2.area() - area_delta < new_feature.area():
                # the intersection is almost covering the entire preexisting area, so just assume that they're identical.
                new_feature = zoning.ZoningFeature("%s->%s" % (f1.objectid, f2.objectid), f2.zoning, f2.geometry, f2.old_zoning + f1.zoning)
            else:
                # add a new feature containing the portion of f2 that does not intersect with f1
                new_geom = f2.geometry.difference(new_feature.geometry)
                if not new_geom.is_empty:
                    map2.append(zoning.ZoningFeature("%s.2" % f2.objectid, f2.zoning, new_geom, f2.old_zoning))
                    estimator.end_value = len(map1) * len(map2)
                    new_state[1] = map2[-1]
            map2[i] = new_feature
            new_state[0] = map2[i]
            logger("\r%s\rPlot %s (%.02f acres) -> %s (%.02f acres) went from %s to %s\n" % (' ' * 40, f1.objectid, zoning.square_meters_to_acres(f1.area()), f2.objectid, zoning.square_meters_to_acres(new_feature.area()), f1.zoning, f2.zoning))
            estimator.force_next_refresh()
            # Delete the portion of overlap in f1 to hopefully speed up further comparisons:
            # (This is making the assumption that the zoning regions in map2 are non-overlapping)
            map1[n] = zoning.ZoningFeature(f1.objectid, f1.zoning, f1.geometry.difference(isect))
            new_state[2] = map1[n]
            saver.record(n, i, *new_state)
            if incremental_save_path and estimator.get_time() - last_incremental_save >= incremental_save_time:
                # do an incremental save once every incremental_save_time seconds
                logger("\r%s\rDoing an incremental save to %s..." % (' ' * 40, incremental_save_path))
                last_incremental_save = estimator.get_time()
                with open(incremental_save_path, 'w') as f:
                    map2.save(f)
            if map1[n].geometry.is_empty:
                break
    logger('\n')
    return map2

if __name__ == "__main__":
    import os
    import sys

    with open(sys.argv[1], 'r') as f1:
        with open(sys.argv[2], 'r') as f2:
            def logger(msg):
                sys.stderr.write(msg)
                sys.stderr.flush()
            previous_save = None
            save_state_to = None
            if len(sys.argv) >= 4:
                if os.path.exists(sys.argv[3]):
                    logger('Loading save state...\n')
                    with open(sys.argv[3], 'r') as f:
                        previous_save = load_save_file(f)
                    logger("\r%s\rLoaded.\n" % (' ' * 40))
                save_state_to = open(sys.argv[3], 'a')
            try:
                intersected = intersect(zoning.ZoningMap(f1), zoning.ZoningMap(f2), logger = logger, previous_save = previous_save, save_state_to = save_state_to, incremental_save_path = "%s.incremental" % sys.argv[3])
            finally:
                if save_state_to is not None:
                    save_state_to.close()
            intersected.save(sys.stdout)
            os.unlink("%s.incremental" % sys.argv[3])
            ## Sanity check:
            #import StringIO
            #output = StringIO.StringIO()
            #intersected.save(output)
            #output.seek(0)
            #list(zoning.ZoningMap(output))
            #output.close()
