import itertools
import json
from osgeo import ogr

class ZoningFeature(object):
    def __init__(self, zoning, geometry, old_zoning = None):
        self.zoning = zoning
        if old_zoning is None:
            old_zoning = []
        self.old_zoning = old_zoning
        self.geometry = geometry
    #def __getattr__(self, key):
    #    return getattr(self._parent_feature, key)

class ZoningMap(object):
    def __init__(self, path):
        driver = ogr.GetDriverByName('GeoJSON')
        datasource = driver.Open(path)
        self._layer = datasource.GetLayer()
        self._features = []
        for i in range(len(self._layer)):
            ogr_feature = self._layer.GetNextFeature()
            try:
                zoning = ogr_feature.GetField("LONG_CODE")
            except Exception:
                zoning = (ogr_feature.GetField("CODE"), ogr_feature.GetField("CATEGORY"))
            self._features.append(ZoningFeature([zoning], ogr_feature.GetGeometryRef()))
    def __len__(self):
        return len(self._features)
    #    return len(self._layer)
    def __getitem__(self, key):
        return self._features[key]
    #    if key < 0 or key >= len(self):
    #        return None
    #    while key >= len(self._features):
    #        self._features.append(ZoningFeature(self._layer.GetNextFeature()))
    #    return self._features[key]
    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

def intersect(map1, map2):
    changed = True
    features1 = [feat for feat in map1]
    features2 = [feat for feat in map2]
    while changed:
        changed = False
        for i, j in itertools.product(range(len(features1)), range(len(features2))):
            f1 = features1[i]
            f2 = features2[j]
            isect = f1.geometry.Intersection(f2.geometry)
            if not isect.IsEmpty():
                changed = True
                print "GGGG"
                oldf1 = f1.geometry
                f1 = ZoningFeature(f1.zoning, f1.geometry.Difference(isect))
                features1.append(ZoningFeature(f1.zoning, oldf1.Difference(f1.geometry)))
                oldf2 = f2.geometry
                f2 = ZoningFeature(f2.zoning, f2.geometry.Difference(isect), f2.old_zoning + f1.zoning)
                print "Found a plot that went from %s to %s" % (f1.zoning, f2.zoning)
                features2.append(ZoningFeature(f2.zoning, oldf2.Difference(f2.geometry)))
                exit(0)
                break
                
if __name__ == "__main__":
    import sys

    intersect(ZoningMap(sys.argv[1]), ZoningMap(sys.argv[2]))
