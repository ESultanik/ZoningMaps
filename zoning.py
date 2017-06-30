import functools
import json
import pyproj
from shapely.geometry import mapping, MultiPolygon, Point, Polygon, shape
import shapely.ops

def square_meters_to_acres(m2):
    return m2 * 0.000247105

def square_meters_to_square_feet(m2):
    return m2 * 10.7639

class ZoningFeature(object):
    def __init__(self, objectid, zoning, geometry, old_zoning = None):
        self.objectid = objectid
        self.zoning = zoning
        if old_zoning is None:
            old_zoning = []
        self.old_zoning = old_zoning
        self.geometry = geometry
        self._area = None
    def area(self):
        """Calculates the area of this zoning feature in square meters"""
        if self.geometry.is_empty:
            return 0.0
        elif self._area is None:
            geom_aea = shapely.ops.transform(
                functools.partial(
                    pyproj.transform,
                    pyproj.Proj(init='EPSG:4326'),
                    pyproj.Proj(
                        proj='aea',
                        lat1=self.geometry.bounds[1],
                        lat2=self.geometry.bounds[3])),
                self.geometry)
            self._area = geom_aea.area
        return self._area
    def distance_to(self, lat, lon):
        proj = pyproj.Proj(
                    proj='aea',
                    lat1=self.geometry.bounds[1],
                    lat2=self.geometry.bounds[3])
        transform = functools.partial(
                pyproj.transform,
                pyproj.Proj(init='EPSG:4326'),
                proj)
        geom_aea = shapely.ops.transform(transform, self.geometry)
        point_aea = shapely.ops.transform(transform, Point(lon, lat))
        return geom_aea.distance(point_aea)
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

def parse_feature(geojson):
    properties = geojson["properties"]
    if "LONG_CODE" in properties:
        zoning = properties["LONG_CODE"]
    else:
        zoning = (properties["CODE"], properties["CATEGORY"])
    if "OLD_ZONING" in properties:
        old_zoning = properties["OLD_ZONING"]
    else:
        old_zoning = None
    return ZoningFeature(properties["OBJECTID"], [zoning], shape(geojson["geometry"]), old_zoning)

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
            self._features.append(parse_feature(self.json["features"][key]))
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
