import itertools
import json
from shapely.geometry import mapping, MultiPolygon, Polygon, shape
import time

class ZoningFeature(object):
    def __init__(self, objectid, zoning, geometry, old_zoning = None):
        self.objectid = objectid
        self.zoning = zoning
        if old_zoning is None:
            old_zoning = []
        self.old_zoning = old_zoning
        self.geometry = geometry
    def to_geo(self):
        properties = {
            "OBJECTID":self.objectid,
        }
        if self.old_zoning is not None:
            properties["OLD_ZONING"] = self.old_zoning
        if (type(self.zoning) == tuple or type(self.zoning) == list) and len(self.zoning) == 2:
            properties["CODE"], properties["CATEGORY"] = self.zoning
        else:
            properties["LONG_CODE"] = self.zoning
        return {
            "type":"Feature",
            "properties":properties,
            "geometry":mapping(self.geometry)
            }

class ZoningMap(object):
    def __init__(self, stream):
        self.json = json.load(stream)
        self._features = []
    def save(self, outstream):
        json.dump(self.json, outstream)
    def __len__(self):
        return len(self.json["features"])
    def __getitem__(self, key):
        if key < 0 or key >= len(self):
            return None
        while key >= len(self._features):
            feature = self.json["features"][key]
            #poly = None
            #try:
            #    poly = [Polygon(coords) for coords in feature["geometry"]["coordinates"]]
            #except ValueError as e:
            #    print feature["geometry"]["coordinates"]
            #    print e
            #    exit(3)
            #if len(poly) == 1:
            #    poly = poly[0]
            #else:
            #    poly = MultiPolygon(*poly)
            properties = feature["properties"]
            if "LONG_CODE" in properties:
                zoning = properties["LONG_CODE"]
            else:
                zoning = (properties["CODE"], properties["CATEGORY"])
            if "OLD_ZONING" in properties:
                old_zoning = properties["OLD_ZONING"]
            else:
                old_zoning = None
            self._features.append(ZoningFeature(properties["OBJECTID"], [zoning], shape(feature["geometry"]), old_zoning))
        return self._features[key]
    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

class ModifiableMap(object):
    def __init__(self, zmap):
        self.zmap = zmap
        self._feature_iter = iter(zmap)
        self._cache = []
        self._appended = []
    def save(self, outstream):
        features = [feature.to_geo() for feature in self]
        json.dump({"type":"FeatureCollection","features":features}, outstream)
    def __len__(self):
        return len(self.zmap) + len(self._appended)
    def __getitem__(self, key):
        if key < 0 or key >= len(self):
            return None
        elif key < len(self.zmap):
            while key >= len(self._cache):
                self._cache.append(next(self._feature_iter))
            return self._cache[key]
        else:
            return self._appended[key - len(self.zmap)]
    def __setitem__(self, key, value):
        old_val = self[key]
        if old_val is not None:
            if key < len(self.zmap):
                self._cache[key] = value
            else:
                self._appended[key - len(self.zmap)] = value
        return old_val
    def append(self, feature):
        self._appended.append(feature)
    def __iter__(self):
        for i in range(len(self)):
            yield self[i]
        
def intersect(map1, map2, logger = None):
    if logger is None:
        logger = lambda m : None
    map1 = ModifiableMap(map1)
    map2 = ModifiableMap(map2)
    last_percent = -1
    last_log_time = 0
    start_time = time.time()
    for n, f1 in enumerate(map1):
        for i, f2 in enumerate(map2):
            raw_percent = float((n * len(map2) + i) * 10000) / float(len(map1) * len(map2))
            percent = float(int(raw_percent)) / 100.0
            raw_percent /= 100.0
            current_time = time.time()
            if percent > last_percent or current_time - last_log_time >= 3:
                if raw_percent == 0:
                    time_remaining = "????"
                else:
                    seconds_remaining = (current_time - start_time) / raw_percent * (100.0 - raw_percent)
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
                logger("\r%s\r%.2f%% %s remaining" % (' ' * 40, percent, time_remaining))
                last_percent = percent
                last_log_time = current_time
            isect = f1.geometry.intersection(f2.geometry)
            if isect.is_empty:
                continue
            map2[i] = ZoningFeature("%s->%s" % (f1.objectid, f2.objectid), f2.zoning, f2.geometry.difference(isect), f2.old_zoning + f1.zoning)
            logger("\r%s\rPlot %s -> %s went from %s to %s\n" % (' ' * 40, f1.objectid, f2.objectid, f1.zoning, f2.zoning))
            last_percent = -1
            map2.append(ZoningFeature("%s.2" % f2.objectid, f2.zoning, f2.geometry.difference(map2[i].geometry)))
            # Delete the portion of overlap in f1 to hopefully speed up further comparisons:
            map1[n] = ZoningFeature(f1.objectid, f1.zoning, f1.geometry.difference(isect))
            if map1[n].geometry.is_empty:
                break
    logger('\n')
    return map2

if __name__ == "__main__":
    import sys

    with open(sys.argv[1], 'r') as f1:
        with open(sys.argv[2], 'r') as f2:
            def logger(msg):
                sys.stderr.write(msg)
                sys.stderr.flush()
            intersected = intersect(ZoningMap(f1), ZoningMap(f2), logger = logger)
            intersected.save(sys.stdout)
            ## Sanity check:
            #import StringIO
            #output = StringIO.StringIO()
            #intersected.save(output)
            #output.seek(0)
            #list(ZoningMap(output))
            #output.close()
