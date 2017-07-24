import csv
import os
import scipy.spatial

import philly

PROPERTY_DATA_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "opa_properties_public.csv")

class Property(object):
    def __init__(self):
        pass
    def get_zoning(self):
        code = self.zoning.strip()
        if not code:
            return None
        elif code in philly.ZONING:
            return philly.ZONING[code]
        elif ord(code[-1]) >= ord('0') and ord(code[-1]) <= ord('9'):
            code = "%s-%d" % (code[:-1], int(code[-1]))
            if code in philly.ZONING:
                return philly.ZONING[code]
        return None
    def residential_capacity(self):
        zoning = self.get_zoning()
        if zoning is None:
            return 1.0
        max_residents = zoning.resident_bounds(float(self.total_area))[1]
        if max_residents == 0:
            return 1.0
        return min(1.0, (float(self.total_livable_area) / 450.0) / max_residents)

def load_opm_property_data(path = None):
    if path is None:
        path = PROPERTY_DATA_FILE
    header = None
    with open(path, "rb") as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if header is None:
                header = row
                continue
            p = Property()
            for i, v in enumerate(row):
                setattr(p, header[i], v)
            yield p

def field_to_float(obj, field_name):
    try:
        setattr(obj, field_name, float(getattr(obj, field_name)))
    except ValueError:
        setattr(obj, field_name, 0.0)
            
def compile_data():
    points = []
    data = []
    for p in load_opm_property_data():
        try:
            points.append((float(p.lat), float(p.lng)))
        except ValueError:
            pass
        for field in ("market_value", "total_livable_area", "taxable_building", "taxable_land"):
            field_to_float(p, field)
        data.append(p)
    kdtree = scipy.spatial.KDTree(points)
    return points, data, kdtree    
            
if __name__ == "__main__":
    points, data, kdtree = compile_data()

    import sys

    import zoning

    with open(sys.argv[1], 'r') as f:
        zmap = zoning.ZoningMap(f)
        for feature in zmap:
            fzoning = feature.zoning
            while type(fzoning) == list and len(fzoning) == 1:
                fzoning = fzoning[0]
            fzoning = str(fzoning)
            if fzoning not in philly.ZONING:
                continue
            feature_value = 0.0
            feature_livable_area = 0.0
            for i in feature.find_contained_points(points, kdtree):
                feature_value += data[i].market_value
                feature_livable_area += data[i].total_livable_area
            bound = philly.ZONING[fzoning].resident_bounds(zoning.square_meters_to_square_feet(feature.area()))[1]
            if bound == 0:
                bound = 1.0
            else:
                bound = min(1.0, (feature_livable_area / 450.0) / bound)
            if bound == 0:
                value_diff = 0.0
            else:
                value_diff = feature_value / min(1.0, (feature_livable_area / 450.0) / bound) - feature_value
            print bound, value_diff
