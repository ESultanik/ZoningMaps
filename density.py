from fastkml import kml
import fastkml
import shapely
import sys

import philly
import zoning

class MappingMode:
    SQFT      = "sqft"
    RESIDENCY = "residency"

class MaxDistrict(object):
    def __init__(self, new_district, sqft, value_function):
        self.values = []
        self.value_function = value_function
        self.new_max = value_function(new_district, sqft)
        self.new_district = new_district
        self.old_max = None
        self.old_districts = []
        self.sqft = sqft
    def add(self, old_district):
        self.old_districts.append(old_district)
        self.values.append(self.value_function(old_district, self.sqft))
        self.old_max = max(self.values)
    def get_placemark(self):
        if self.new_max == self.old_max:
            return None, None
        elif self.old_max == 0:
            change = "infinite increase"
            color = "ff00ff00"
        elif self.new_max > self.old_max:
            change = "%.2f%% increase" % (((self.new_max / self.old_max) - 1.0) * 100.0)
            color = "%s00ff00" % hex(int(min(((self.new_max / self.old_max) - 1.0), 1.0) * 128 + 0.5))[2:]
        else:
            change = "%.2f%% decrease" % ((1.0 - (self.new_max / self.old_max)) * 100.0)
            color = "%s0000ff" % hex(int(min((1.0 - (self.new_max / self.old_max)), 1.0) * 128 + 0.5))[2:]
        return "%s => %s (%s)" % (self.old_max, self.new_max, change), color
    
class MaxValueMetric(object):
    def __init__(self, name, value_function):
        self.name = name
        self.value_function = value_function
        self.old_value = 0
        self.new_value = 0
    def new_district(self, *args):
        return MaxDistrict(*args, value_function = self.value_function)
    def add_district(self, district):
        if district.values:
            self.old_value += district.old_max
            self.new_value += district.new_max
            return True
        return False
    def finalize(self):
        sys.stderr.write(" Pre-2012 %s: %s\n" % (self.name, self.old_value))
        sys.stderr.write("Post-2012 %s: %s\n" % (self.name, self.new_value))

def map_to_kml(zoning_map, metric = None):
    if metric is None:
        metric = MaxValueMetric("maximum residency", lambda district, sqft : district.resident_bounds(sqft)[1])
    k = kml.KML()
    ns = '{http://www.opengis.net/kml/2.2}'
    d = kml.Document(ns, 'PHL Zoning Density Changes', 'Philadelphia Residential Zoning Density Changes 2012 to 2017', 'A map of the density changes between current (2017) zoning plots and the previous (Pre-2012) classifications.')
    k.append(d)
    f = kml.Folder(ns, 'PHL Zoning Density', 'Philadelphia Zoning Density', 'Changes to Philadelphia zoning density from 2012 to 2017')
    d.append(f)
    for feature in zoning_map:
        fzoning = feature.zoning
        while type(fzoning) == list and len(fzoning) == 1:
            fzoning = fzoning[0]
        fzoning = str(fzoning)
        if fzoning not in philly.ZONING:
            continue
        elif not feature.old_zoning:
            continue
        zonings = []
        lot_sqft = zoning.square_meters_to_square_feet(feature.area())
        district = metric.new_district(philly.ZONING[fzoning], lot_sqft)
        for z in feature.old_zoning:
            zonings.append(' '.join(z))
            if z[0] in philly.ZONING:
                district.add(philly.ZONING[z[0]])
        old_zoning = " and ".join(zonings)
        if not metric.add_district(district):
            continue
        if feature.geometry.geom_type == "Polygon":
            polygons = [feature.geometry]
        else:
            allparts = [p.buffer(0) for p in feature.geometry]
            polygons = [shapely.ops.cascaded_union(allparts)]
        message, color = district.get_placemark()
        if message is not None:
            for poly in polygons:
                p = kml.Placemark(ns, str(feature.objectid), "%s => %s" % (old_zoning, fzoning), "%d sqft.; %s %s" % (int(lot_sqft + 0.5), metric.name, message))
                p.append_style(fastkml.styles.Style(ns=ns, styles=[fastkml.styles.PolyStyle(ns=ns, color=color, fill=1, outline=0)]))
                p.geometry = poly
                f.append(p)
    metric.finalize()
    return k

if __name__ == "__main__":
    import sys

    metric = None
    path = None

    if sys.argv[1] == '-sqft':
        metric = MaxValueMetric("maximum sqft.", lambda district, sqft : district.estimate_maximum_sqft(sqft))
        path = sys.argv[2]
    elif sys.argv[1] == '-residency':
        path = sys.argv[2]
    else:
        path = sys.argv[1]
    
    with open(path, 'r') as f:
        print map_to_kml(zoning.ZoningMap(f), metric = metric).to_string(prettyprint=True)
