from fastkml import kml
import fastkml

import zoning

def map_to_kml(zoning_map):
    k = kml.KML()
    ns = '{http://www.opengis.net/kml/2.2}'
    d = kml.Document(ns, 'docid', 'doc name', 'doc description')
    k.append(d)
    f = kml.Folder(ns, 'PHL Zoning', 'Philadelphia Zoning', 'Changes to Philadelphia zoning from 2012 to 2017')
    d.append(f)
    zoning_colors = {
        ("RSD-1", "RSD-2", "RSD-3") : (245, 240, 192),
        ("RSA-1", "RSA-2", "RSA-3") : (244, 239, 103),
        ("RSA-4", "RSA-5") : (240, 235, 101),
        ("RTA-1",) : (205, 181, 78),
        ("RM-1", "RM-2", "RM-3") : (252, 184, 80),
        }
    zoning_styles = {}
    for classes, rgb in zoning_colors.iteritems():
        hexstyle = "7f%02x%02x%02x" % tuple(reversed(rgb))
        style = fastkml.styles.Style(ns=ns, styles=[fastkml.styles.PolyStyle(ns=ns, color=hexstyle, fill=1, outline=1)])
        for c in classes:
            zoning_styles[c] = style
    for feature in zoning_map:
        if feature.geometry.geom_type == "Polygon":
            #polygons = [feature]
            pass
        else:
            continue
            #allparts = [p.buffer(0) for p in feature.geometry]
            #poly.geometry = shapely.ops.cascaded_union(allparts)
            #x, y = poly.geometry.exterior.xy  # here happens the error

            #import sys
            #sys.stderr.write(feature.geometry.geom_type + "\n")
            #exit(1)
        p = kml.Placemark(ns, str(feature.objectid), str(feature.zoning), "Pre-2012 Zoning: %s" % (', '.join(map(str, feature.old_zoning))))
        zoning = feature.zoning
        while type(zoning) == list and len(zoning) == 1:
            zoning = zoning[0]
        zoning = str(zoning)
        if zoning in zoning_styles:
            p.append_style(zoning_styles[zoning])
        p.geometry = feature.geometry
        f.append(p)
    return k
#def make_zoning_kml():


    
if __name__ == "__main__":
    import sys

    #make_zoning_kml(
    with open(sys.argv[1], 'r') as f:
        print map_to_kml(zoning.ZoningMap(f)).to_string(prettyprint=True)
