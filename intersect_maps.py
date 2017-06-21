import progress
import zoning

def intersect(map1, map2, logger = None):
    if logger is None:
        logger = lambda m : None
    map1 = zoning.ModifiableMap(map1)
    map2 = zoning.ModifiableMap(map2)
    estimator = progress.TimeEstimator(logger, 0, len(map1) * len(map2), precision = 2, interval = 3.0)
    for n, f1 in enumerate(map1):
        if f1.geometry.is_empty:
            continue
        for i, f2 in enumerate(map2):
            estimator.update(n * len(map2) + i)
            if f2.geometry.is_empty:
                continue
            try:
                isect = f1.geometry.intersection(f2.geometry)
            except Exception as e:
                logger("\r%s\rError: %s\n" % (' ' * 40, e))
                estimator.force_next_refresh()
                continue
            if isect.is_empty:
                continue
            area_delta = 10.0 # square meters
            new_feature = zoning.ZoningFeature("%s->%s" % (f1.objectid, f2.objectid), f2.zoning, isect, f2.old_zoning + f1.zoning)
            if new_feature.area() < area_delta:
                # The intersection is less than area_delta square meters, so it's probably just floating point error.
                # Skip it!
                continue
            elif f2.area() - area_delta < new_feature.area():
                # the intersection is almost covering the entire preexisting area, so just assume that they're identical.
                new_feature = zoning.ZoningFeature("%s->%s" % (f1.objectid, f2.objectid), f2.zoning, f2.geometry, f2.old_zoning + f1.zoning)
            else:
                # add a new feature containing the portion of f2 that does not intersect with f1
                new_geom = f2.geometry.difference(new_feature.geometry)
                if not new_geom.is_empty:
                    map2.append(zoning.ZoningFeature("%s.2" % f2.objectid, f2.zoning, new_geom, f2.old_zoning))
            map2[i] = new_feature
            logger("\r%s\rPlot %s (%.02f acres) -> %s (%.02f acres) went from %s to %s\n" % (' ' * 40, f1.objectid, zoning.square_meters_to_acres(f1.area()), f2.objectid, zoning.square_meters_to_acres(new_feature.area()), f1.zoning, f2.zoning))
            estimator.force_next_refresh()
            # Delete the portion of overlap in f1 to hopefully speed up further comparisons:
            # (This is making the assumption that the zoning regions in map2 are non-overlapping)
            map1[n] = zoning.ZoningFeature(f1.objectid, f1.zoning, f1.geometry.difference(isect))
            if map1[n].geometry.is_empty:
                break
    logger('\n')
    return map2

if __name__ == "__main__":
    import sys

    with open(sys.argv[1], 'r') as f1:
        with open(sys.argv[2], 'r') as f2:
            def logger(msg):
                sys.stderr.write(msg)
                sys.stderr.flush()
            intersected = intersect(zoning.ZoningMap(f1), zoning.ZoningMap(f2), logger = logger)
            intersected.save(sys.stdout)
            ## Sanity check:
            #import StringIO
            #output = StringIO.StringIO()
            #intersected.save(output)
            #output.seek(0)
            #list(zoning.ZoningMap(output))
            #output.close()
