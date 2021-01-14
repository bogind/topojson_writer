# QGIS TopoJson writer

A QGIS plugin to write vector layers into TopoJson files

The plugin creates a temporary geojson from your layer (deleted after conversion) and the uses [topojson-server](https://github.com/topojson/topojson-server) to convert it to topojson and save on your system.
All output topojson have their CRS transformed to WGS84 (EPSG:4326)

### Note: the process will work slower on large layers, and layers with complex geometry.

topojson-server and the rest of the topojson js suite created by [Mike Bostock](https://github.com/mbostock)