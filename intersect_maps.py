import json
import progress
import zoning

def load_save_file(stream):
    save = {}
    for line in stream:
        data = json.loads(line)
        if data[2] is None:
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
    def record(self, n, i, *args):
        if self.stream is None:
            return
        if args:
            a = []
            for arg in args:
                if arg is None:
                    a.append(None)
                else:
                    a.append(arg.to_geo())
            self.stream.write(json.dumps([n, i] + a))
        else:
            self.stream.write(json.dumps([n, i, None]))
        self.stream.write('\n')
        self.current_state_flush += 1
        if (self.current_state_flush - self.last_state_flush) >= self.flush_interval:
            self.last_state_flush = self.current_state_flush
            self.stream.flush()

def intersect(map1, map2, logger = None, previous_save = None, save_state_to = None):
    if logger is None:
        logger = lambda m : None
    map1 = zoning.ModifiableMap(map1)
    map2 = zoning.ModifiableMap(map2)
    estimator = progress.TimeEstimator(logger, 0, len(map1) * len(map2), precision = 2, interval = 3.0)
    if previous_save is not None:
        logger("\r%s\rFast-forwarding using saved state..." % (' ' * 40))
    saver = StateSaver(save_state_to)
    for n, f1 in enumerate(map1):
        if f1.geometry.is_empty:
            continue
        for i, f2 in enumerate(map2):
            if previous_save is not None and (n, i) in previous_save:
                state = previous_save[(n,i)]
                if state is None:
                    continue
                map2[i] = state[0]
                if state[1] is not None:
                    map2.append(state[1])
                map1[n] = state[2]
                if map1[n].geometry.is_empty:
                    break
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
                    logger('Loading save state...')
                    with open(sys.argv[3], 'r') as f:
                        previous_save = load_save_file(f)
                    logger('\n')
                save_state_to = open(sys.argv[3], 'a')
            try:
                intersected = intersect(zoning.ZoningMap(f1), zoning.ZoningMap(f2), logger = logger, previous_save = previous_save, save_state_to = save_state_to)
            finally:
                if save_state_to is not None:
                    save_state_to.close()
            intersected.save(sys.stdout)
            ## Sanity check:
            #import StringIO
            #output = StringIO.StringIO()
            #intersected.save(output)
            #output.seek(0)
            #list(zoning.ZoningMap(output))
            #output.close()
