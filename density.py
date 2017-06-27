from fastkml import kml
import fastkml
import shapely
import sys

import philly
import zoning

class MappingMode:
    SQFT      = "sqft"
    RESIDENCY = "residency"

class ResidencyMetric(object):
    def __init__(self):
        self.old_occupancy = 0
        self.new_occupancy = 0
    def new_district(self, *args):
        class District(object):
            def __init__(self, new_district, sqft):
                self.occupancies = []
                self.new_max_occupancy = new_district.resident_bounds(sqft)[1]
                self.new_district = new_district
                self.old_max_occupancy = None
                self.old_districts = []
                self.sqft = sqft
            def add(self, old_district):
                self.old_districts.append(old_district)
                self.occupancies.append(old_district.resident_bounds(self.sqft)[1])
                self.old_max_occupancy = max(self.occupancies)
            def get_placemark(self):
                if self.new_max_occupancy == self.old_max_occupancy:
                    return None, None
                elif self.new_max_occupancy > self.old_max_occupancy:
                    occupancy_change = "%.2f%% increase" % (((self.new_max_occupancy / self.old_max_occupancy) - 1.0) * 100.0)
                    color = "%s00ff00" % hex(int(min(((self.new_max_occupancy / self.old_max_occupancy) - 1.0), 1.0) * 128 + 0.5))[2:]
                else:
                    occupancy_change = "%.2f%% decrease" % ((1.0 - (self.new_max_occupancy / self.old_max_occupancy)) * 100.0)
                    color = "%s0000ff" % hex(int(min((1.0 - (self.new_max_occupancy / self.old_max_occupancy)), 1.0) * 128 + 0.5))[2:]
                return "Maximum occupancy: %s => %s (%s)" % (self.old_max_occupancy, self.new_max_occupancy, occupancy_change), color
        return District(*args)
    def add_district(self, district):
        if district.occupancies:
            self.old_occupancy += district.old_max_occupancy
            self.new_occupancy += district.new_max_occupancy
            return True
        return False
    def finalize(self):
        sys.stderr.write(" Pre-2012 maximum occupancy in residential zoning: %s\n" % self.old_occupancy)
        sys.stderr.write("Post-2012 maximum occupancy in residential zoning: %s\n" % self.new_occupancy)

def map_to_kml(zoning_map, metric = None):
    if metric is None:
        metric = ResidencyMetric()
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
                p = kml.Placemark(ns, str(feature.objectid), "%s => %s" % (old_zoning, fzoning), "%d sqft.; %s" % (int(lot_sqft + 0.5), message))
                p.append_style(fastkml.styles.Style(ns=ns, styles=[fastkml.styles.PolyStyle(ns=ns, color=color, fill=1, outline=0)]))
                p.geometry = poly
                f.append(p)
    metric.finalize()
    return k

if __name__ == "__main__":
    import sys

    with open(sys.argv[1], 'r') as f:
        print map_to_kml(zoning.ZoningMap(f)).to_string(prettyprint=True)
