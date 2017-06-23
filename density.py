from fastkml import kml
import fastkml
import shapely
import sys

import philly
import zoning

def map_to_kml(zoning_map):
    k = kml.KML()
    ns = '{http://www.opengis.net/kml/2.2}'
    d = kml.Document(ns, 'PHL Zoning Density Changes', 'Philadelphia Residential Zoning Density Changes 2012 to 2017', 'A map of the density changes between current (2017) zoning plots and the previous (Pre-2012) classifications.')
    k.append(d)
    f = kml.Folder(ns, 'PHL Zoning Density', 'Philadelphia Zoning Density', 'Changes to Philadelphia zoning density from 2012 to 2017')
    d.append(f)
    old_occupancy = 0
    new_occupancy = 0
    for feature in zoning_map:
        fzoning = feature.zoning
        while type(fzoning) == list and len(fzoning) == 1:
            fzoning = fzoning[0]
        fzoning = str(fzoning)
        if fzoning not in philly.ZONING:
            continue
        elif not feature.old_zoning:
            continue
        occupancies = []
        zonings = []
        for z in feature.old_zoning:
            zonings.append(' '.join(z))
            if z[0] in philly.ZONING:
                lot_sqft = zoning.square_meters_to_square_feet(feature.area())
                occupancies.append(philly.ZONING[z[0]].resident_bounds(lot_sqft)[1])
        old_zoning = " and ".join(zonings)
        if not occupancies:
            continue
        old_max_occupancy = max(occupancies)
        max_occupancy = philly.ZONING[fzoning].resident_bounds(lot_sqft)[1]
        old_occupancy += old_max_occupancy
        new_occupancy += max_occupancy
        if feature.geometry.geom_type == "Polygon":
            polygons = [feature.geometry]
        else:
            allparts = [p.buffer(0) for p in feature.geometry]
            polygons = [shapely.ops.cascaded_union(allparts)]
        for poly in polygons:
            if max_occupancy == old_max_occupancy:
                continue
                occupancy_change = "no change"
            elif max_occupancy > old_max_occupancy:
                occupancy_change = "%.2f%% increase" % (((max_occupancy / old_max_occupancy) - 1.0) * 100.0)
                color = "%s00ff00" % hex(int(min(((max_occupancy / old_max_occupancy) - 1.0), 1.0) * 128 + 0.5))[2:]
            else:
                occupancy_change = "%.2f%% decrease" % ((1.0 - (max_occupancy / old_max_occupancy)) * 100.0)
                color = "%s0000ff" % hex(int(min((1.0 - (max_occupancy / old_max_occupancy)), 1.0) * 128 + 0.5))[2:]
            p = kml.Placemark(ns, str(feature.objectid), "%s => %s" % (old_zoning, fzoning), "%d sqft.; Maximum occupancy: %s => %s (%s)" % (int(lot_sqft + 0.5), old_max_occupancy, max_occupancy, occupancy_change))
            p.append_style(fastkml.styles.Style(ns=ns, styles=[fastkml.styles.PolyStyle(ns=ns, color=color, fill=1, outline=0)]))
            p.geometry = poly
            f.append(p)
    sys.stderr.write(" Pre-2012 maximum occupancy in residential zoning: %s\n" % old_occupancy)
    sys.stderr.write("Post-2012 maximum occupancy in residential zoning: %s\n" % new_occupancy)
    return k

if __name__ == "__main__":
    import sys

    with open(sys.argv[1], 'r') as f:
        print map_to_kml(zoning.ZoningMap(f)).to_string(prettyprint=True)
