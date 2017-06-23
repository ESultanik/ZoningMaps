from fastkml import kml
import fastkml

import shapely
import zoning

def map_to_kml(zoning_map):
    k = kml.KML()
    ns = '{http://www.opengis.net/kml/2.2}'
    d = kml.Document(ns, 'PHL Zoning Changes', 'Philadelphia Zoning Changes 2012 to 2017', 'A map of current (2017) zoning plots along with the previous (Pre-2012) classifications.')
    k.append(d)
    f = kml.Folder(ns, 'PHL Zoning', 'Philadelphia Zoning', 'Changes to Philadelphia zoning from 2012 to 2017')
    d.append(f)
    zoning_colors = {
        ("RSD-1", "RSD-2", "RSD-3") : (245, 240, 192),
        ("RSA-1", "RSA-2", "RSA-3") : (244, 239, 103),
        ("RSA-4", "RSA-5") : (240, 235, 101),
        ("RTA-1",) : (205, 181, 78),
        ("RM-%d" % i for i in range(1,5)) : (252, 184, 80),
        ("RMX-1", "RMX-2", "RMX-3") : (230, 132, 37),
        ("CMX-1", "CMX-2", "CMX-2.5") : (241, 102, 103),
        ("CMX-3", "CMX-4") : (238, 33, 35),
        ("CMX-5",) : (177, 31, 36),
        ("CA-1", "CA-2") : (247, 161, 163),
        ("IRMX",) : (212, 165, 120),
        ("ICMX",) : (220, 190, 218),
        ("I-1",) : (178, 127, 183),
        ("I-2",) : (135, 74, 157),
        ("I-3",) : (84, 71, 157),
        ("I-P",) : (129, 126, 188),
        ("SP-PO-A", "SP-PO-P") : (0, 255, 0),
        ("SP-INS",) : (235, 232, 197),
        ("SP-ENT",) : (235, 0, 0),
        ("SP-STA",) : (255, 0, 0),
        }
    zoning_styles = {}
    for classes, rgb in zoning_colors.iteritems():
        hexstyle = "7f%02x%02x%02x" % tuple(reversed(rgb))
        style = fastkml.styles.Style(ns=ns, styles=[fastkml.styles.PolyStyle(ns=ns, color=hexstyle, fill=1, outline=1)])
        for c in classes:
            zoning_styles[c] = style
    for feature in zoning_map:
        if feature.geometry.geom_type == "Polygon":
            polygons = [feature.geometry]
        else:
            allparts = [p.buffer(0) for p in feature.geometry]
            polygons = [shapely.ops.cascaded_union(allparts)]
        zoning = feature.zoning
        while type(zoning) == list and len(zoning) == 1:
            zoning = zoning[0]
        zoning = str(zoning)
        if feature.old_zoning:
            old_zoning = " and ".join(map(lambda z : ' '.join(z), feature.old_zoning))
        else:
            old_zoning = "N/A"
        for poly in polygons:
            p = kml.Placemark(ns, str(feature.objectid), zoning, "Pre-2012 Zoning: %s" % old_zoning)
            if zoning in zoning_styles:
                p.append_style(zoning_styles[zoning])
            p.geometry = poly
            f.append(p)
    return k
#def make_zoning_kml():


    
if __name__ == "__main__":
    import sys

    #make_zoning_kml(
    with open(sys.argv[1], 'r') as f:
        print map_to_kml(zoning.ZoningMap(f)).to_string(prettyprint=True)
