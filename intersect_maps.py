import itertools
import json
from shapely.geometry import MultiPolygon, Polygon, shape

class ZoningFeature(object):
    def __init__(self, objectid, zoning, geometry, old_zoning = None):
        self.objectid = objectid
        self.zoning = zoning
        if old_zoning is None:
            old_zoning = []
        self.old_zoning = old_zoning
        self.geometry = geometry

class ZoningMap(object):
    def __init__(self, stream):
        self.json = json.load(stream)
        self._features = []
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
            self._features.append(ZoningFeature(properties["OBJECTID"], [zoning], shape(feature["geometry"])))
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
    map2 = ModifiableMap(map2)
    last_percent = -1
    for n, f1 in enumerate(map1):
        for i, f2 in enumerate(map2):
            percent = float(int(float((n * len(map2) + i) * 10000) / float(len(map1) * len(map2)))) / 100.0
            if percent > last_percent:
                logger("\r%s\r%.2f%%" % (' ' * 40, percent))
                last_percent = percent
            isect = f1.geometry.intersection(f2.geometry)
            if isect.is_empty:
                continue
            map2[i] = ZoningFeature("%s->%s" % (f1.objectid, f2.objectid), f2.zoning, f2.geometry.difference(isect), f2.old_zoning + f1.zoning)
            logger("\r%s\rPlot %s -> %s went from %s to %s\n" % (' ' * 40, f1.objectid, f2.objectid, f1.zoning, f2.zoning))
            last_percent = -1
            map2.append(ZoningFeature("%s.2" % f2.objectid, f2.zoning, f2.geometry.difference(map2[i].geometry)))
    logger('\n')
    return map2

if __name__ == "__main__":
    import sys

    with open(sys.argv[1], 'r') as f1:
        with open(sys.argv[2], 'r') as f2:
            def logger(msg):
                sys.stderr.write(msg)
                sys.stderr.flush()
            intersect(ZoningMap(f1), ZoningMap(f2), logger = logger)
