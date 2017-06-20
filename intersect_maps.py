import itertools
import json
from shapely.geometry import MultiPolygon, Polygon

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
           poly = [Polygon(coords) for coords in feature["geometry"]["coordinates"]]
           if len(poly) == 1:
               poly = poly[0]
           else:
               poly = MultiPolygon(*poly)
           properties = feature["properties"]
           if "LONG_CODE" in properties:
               zoning = properties["LONG_CODE"]
           else:
               zoning = (properties["CODE"], properties["CATEGORY"])
           self._features.append(ZoningFeature(properties["OBJECTID"], [zoning], poly))
       return self._features[key]
    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

def intersect(map1, map2):
    intersected = []
    for f1 in map1:
        for i in range(len(map2)):
            pass
            
def oldintersect(map1, map2):
    changed = True
    iter1 = iter(map1)
    iter2 = iter(map2)
    features1 = []
    features2 = []
    while changed:
        changed = False
        for i, j in itertools.product(range(len(map1)), range(len(map2))):
            while i >= len(features1):
                features1.append(next(iter1))
            while j >= len(features2):
                features2.append(next(iter2))
            f1 = features1[i]
            f2 = features2[j]
            if f1 is None or f2 is None:
                continue
            isect = f1.geometry.intersection(f2.geometry)
            if not isect.is_empty:
                changed = True
                features1[i] = ZoningFeature(f1.objectid, f1.zoning, f1.geometry.difference(isect))
                if features1[i].geometry.area < 1e-09:
                    features1[i] = None
                new_portion = ZoningFeature("%s.2" % f1.objectid, f1.zoning, f1.geometry.difference(features1[i].geometry))
                features1.append()
                features2[j] = ZoningFeature("%s->%s" % (f1.objectid, f2.objectid), f2.zoning, f2.geometry.difference(isect), f2.old_zoning + f1.zoning)
                print "Plot %s -> %s went from %s to %s" % (f1.objectid, f2.objectid, f1.zoning, f2.zoning)
                features2.append(ZoningFeature("%s.2" % f2.objectid, f2.zoning, f2.geometry.difference(features2[j].geometry)))
                break
            
if __name__ == "__main__":
    import sys

    with open(sys.argv[1], 'r') as f1:
        with open(sys.argv[2], 'r') as f2:
            intersect(ZoningMap(f1), ZoningMap(f2))
