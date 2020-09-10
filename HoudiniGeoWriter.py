import fme, fmeobjects
from lib import utils

'''
This class is intended to be inserted into the FME PythonCaller transformer - it will not
work in any other context.
'''

class HouGeoWriter(object):

	def __init__(self):

		self.bbx = None
		self.point_features = []
		self.line_features = []
		self.poly_features = []

	def input(self, feature):

		'''
		Operate per FMEFeature
		'''

		geomtype = feature.getAttribute("geomtype")
		
		if geomtype == "bbx":
			
			self.bbx = feature.getGeometry()

		elif geomtype == "point":

			self.point_features.append(feature)

		elif geomtype == "polyline":

			self.line_features.append(feature)

		elif geomtype == "polygon":

			self.poly_features.append(feature)

		elif geomtype == "object":

			# Process feature
			geo = utils.processFMESurface(feature)

			# Write .geo string to output feature
			feature.setAttribute("hougeo", geo)

			# Output feature
			self.pyoutput(feature)

		else:

			pass

	def close(self):

		'''
		Operate on all stored FMEFeatures
		'''

		# Create empty list to store outputs
		outputs = []

		# Set the centroid, offset and bounds of the features using provided inputs
		if self.bbx:
			centroid = utils.getCentroid(self.bbx)
			offset = fmeobjects.FMEPoint(-centroid[0], -centroid[1], 0.0)
			bounds = utils.setBounds(offset, self.bbx)

		# Process point features
		if len(self.point_features) > 0:

			# Create output feature to store the .geo string
			out = fmeobjects.FMEFeature()
			out.setAttribute("geomtype", "point")
			out.setAttribute("hougeo", utils.processFMEPoints(self.point_features, centroid, offset, bounds))
			outputs.append(out)

		# Process polyline features
		if len(self.line_features) > 0:
			
			# Create output feature to store the .geo string
			out = fmeobjects.FMEFeature()
			out.setAttribute("geomtype", "polyline")
			out.setAttribute("hougeo", utils.processFMELines(self.line_features, centroid, offset, bounds))
			outputs.append(out)

		# Process polygon features
		if len(self.poly_features) > 0:
			
			# Create output feature to store the .geo string
			out = fmeobjects.FMEFeature()
			out.setAttribute("geomtype", "polygon")
			out.setAttribute("hougeo", utils.processFMEAreas(self.poly_features, centroid, offset, bounds))
			outputs.append(out)

		# Output features
		for out in outputs:
			self.pyoutput(out)