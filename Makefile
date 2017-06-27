.PHONY : all
all : residential_density.kml structural_density.kml intersected.kml

residential_density.kml : intersected.json
	python density.py -residency $< > $@

structural_density.kml : intersected.json
	python density.py -sqft $< > $@

intersected.kml : intersected.json
	python mapping.py $< > $@

intersected.json intersected.json.savestate : | Zoning_PreAug2012.geojson Zoning_BaseDistricts.geojson
	python intersect_maps.py Zoning_PreAug2012.geojson Zoning_BaseDistricts.geojson intersected.json.savestate > $@
