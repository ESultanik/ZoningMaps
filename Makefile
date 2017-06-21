intersected.json intersected.json.savestate : | Zoning_PreAug2012.geojson Zoning_BaseDistricts.geojson
	python intersect_maps.py Zoning_PreAug2012.geojson Zoning_BaseDistricts.geojson intersected.json.savestate > $@
