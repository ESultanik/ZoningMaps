from fastkml import kml
import fastkml
import shapely
import sys

import philly
import progress
import septa
import zoning

class MappingMode:
    SQFT      = "sqft"
    RESIDENCY = "residency"

class MaxDistrict(object):
    def __init__(self, feature, new_district, sqft, value_function):
        self.values = []
        self.value_function = value_function
        self.feature = feature
        self.new_max = value_function(feature, new_district, sqft)
        self.new_district = new_district
        self.old_max = None
        self.old_districts = []
        self.sqft = sqft
    def add(self, old_district):
        self.old_districts.append(old_district)
        self.values.append(self.value_function(self.feature, old_district, self.sqft))
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

class BuiltResidentialCapacity(object):
    def __init__(self, feature, district, sqft, compiled_data):
        self.points, self.data, self.kdtree = compiled_data
        self.feature = feature
        self.district = district
        self.sqft = sqft
        self.feature_value = 0.0
        self.feature_livable_area = 0.0
        self.taxable_building = 0.0
        for i in feature.find_contained_points(self.points, self.kdtree):
            self.feature_value += self.data[i].market_value
            self.feature_livable_area += self.data[i].total_livable_area
            self.taxable_building += self.data[i].taxable_building
        self.value = district.resident_bounds(sqft)[1]
        if self.value == 0:
            self.value = 1.0
        else:
            self.value = min(1.0, (self.feature_livable_area / 450.0) / self.value)
    def add(self, old_district):
        pass
    def get_placemark(self):
        capacity = "%.2f%%" % (self.value * 100.0)
        color = "%s0000ff" % hex(int((1.0 - self.value) * 128.0 + 0.5))[2:]
        return capacity, color

class UnrealizedTaxRevenue(BuiltResidentialCapacity):
    def __init__(self, *args, **kwargs):
        super(UnrealizedTaxRevenue, self).__init__(*args, **kwargs)
        if self.value == 0.0:
            # it is currently at minimum capacity, so say that it has zero potential for additional tax revenue
            # (this is likely incorrect, but would be hard to bound)
            self.value = 0.0
        else:
            self.value = self.taxable_building / self.value
    def get_placemark(self):
        unralized = "%.2f%%" % (self.value * 100.0)
        color = "%s0000ff" % hex(int((1.0 - self.value) * 128.0 + 0.5))[2:]
        return unralized, color
    
class CurrentValueMetric(object):
    def __init__(self, name, metric_class, compiled_data):
        self.name = name
        self.metric_class = metric_class
        self.values = []
        self.compiled_data = compiled_data
    def new_district(self, *args):
        metric = self.metric_class(*args, compiled_data = self.compiled_data)
        self.values.append(metric.value)
        return metric
    def add_district(self, district):
        return True
    def finalize(self):
        sys.stderr.write("Average %s: %.2f\n" % (self.name, float(sum(self.values))/float(len(self.values))))
        
def zoning_data(zoning_map):
    metrics = (
        MaxValueMetric("maximum residency", lambda feature, district, sqft : district.resident_bounds(sqft)[1]),
        MaxValueMetric("maximum sqft.", lambda feature, district, sqft : district.estimate_maximum_sqft(sqft))
    )
    estimator = progress.TimeEstimator(None, 0, len(zoning_map), precision = 1)
    yield tuple(["New Zoning", "Old Zoning"] + reduce(lambda x, y : x + y, map(lambda m : ["New " + m.name, "Old " + m.name], metrics)) + ["Distance to Closest Rapid Transit (meters)"])
    for feature in zoning_map:
        estimator.increment()
        fzoning = feature.zoning
        while type(fzoning) == list and len(fzoning) == 1:
            fzoning = fzoning[0]
        fzoning = str(fzoning)
        if fzoning not in philly.ZONING:
            continue
        elif not feature.old_zoning:
            continue
        zonings = []
        old_zoning = None
        lot_sqft = zoning.square_meters_to_square_feet(feature.area())
        ret = [fzoning]
        for metric in metrics:
            district = metric.new_district(feature, philly.ZONING[fzoning], lot_sqft)
            for z in feature.old_zoning:
                if old_zoning is None:
                    zonings.append(' '.join(z))
                if z[0] in philly.ZONING:
                    district.add(philly.ZONING[z[0]])
            if old_zoning is None:
                old_zoning = " and ".join(zonings)
                ret.append(old_zoning)
            m = metric.add_district(district)
            if not m:
                ret = None
                break
            ret.append(district.new_max)
            ret.append(district.old_max)
        if ret is not None:
            ret.append(min(map(lambda prt : feature.distance_to(prt[0], prt[1]), septa.PHILLY_RAPID_TRANSIT)))
            yield tuple(ret)
    for metric in metrics:
        metric.finalize()
        
def map_to_kml(zoning_map, metric = None):
    if metric is None:
        metric = MaxValueMetric("maximum residency", lambda feature, district, sqft : district.resident_bounds(sqft)[1])
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
        district = metric.new_district(feature, philly.ZONING[fzoning], lot_sqft)
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
    is_raw = False

    if sys.argv[1] == '-sqft':
        metric = MaxValueMetric("maximum sqft.", lambda feature, district, sqft : district.estimate_maximum_sqft(sqft))
        path = sys.argv[2]
    elif sys.argv[1] == '-residency':
        path = sys.argv[2]
    elif sys.argv[1] == '-current-residency':
        path = sys.argv[2]

        import properties

        metric = CurrentValueMetric("built residential capacity", BuiltResidentialCapacity, properties.compile_data())
    elif sys.argv[1] == '-tax':
        path = sys.argv[2]

        import properties

        metric = CurrentValueMetric("unrealized tax revenue", UnrealizedTaxRevenue, properties.compile_data())
    elif sys.argv[1] == '-raw':
        path = sys.argv[2]
        is_raw = True
    else:
        path = sys.argv[1]
    
    with open(path, 'r') as f:
        if is_raw:
            import csv
            csvwriter = csv.writer(sys.stdout, delimiter=',')
            for data in zoning_data(zoning.ZoningMap(f)):
                csvwriter.writerow(data)
        else:
            print map_to_kml(zoning.ZoningMap(f), metric = metric).to_string(prettyprint=True)
