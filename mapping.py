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
    rsa = fastkml.styles.Style(ns=ns, styles=[fastkml.styles.PolyStyle(ns=ns, color="7f00ff00", fill=1, outline=1)])
    assert isinstance(rsa, fastkml.styles._StyleSelector)
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
        if str(zoning).startswith("RSA"):
            p.append_style(rsa)
        p.geometry = feature.geometry
        f.append(p)
    return k
#def make_zoning_kml():


    
if __name__ == "__main__":
    import sys

    #make_zoning_kml(
    with open(sys.argv[1], 'r') as f:
        print map_to_kml(zoning.ZoningMap(f)).to_string(prettyprint=True)
