import json, collections, datetime, socket
from fmehougeo import attrib as ha

'''
This class creates a structured json string that matches the Houdini .geo specification.
It has been designed specifically for the import of Geospatial Datasets into Houdini and
is expected to be used with the associated utilities will convert FME Objects into the
inputs for this class.
'''

class HouGeo(object):

	def __init__(self, bounds):

		self.pt_count = 0
		self.vtx_count = 0
		self.prim_count = 0

		self.bounds = bounds

		self.indices = []

		self.primitives = []

		self.pt_attribs = []
		self.vtx_attribs = []
		self.prim_attribs = []
		self.global_attribs = []

		self.pt_groups = []
		self.vtx_groups = []
		self.prim_groups = []
		self.edge_groups = []

	# ----------------------------------------

	def setPoints(self, points):

		p_attrib = ha.HouAttribute("P", "point", "vec3float", points, special="ppos")
		self.pt_attribs.append(p_attrib.getJSON())
		self.pt_count = len(points)

	# ----------------------------------------

	def setIndices(self, indices):

		self.indices = indices

	# ----------------------------------------

	def setPrimitives(self, ptype, nprims, nverts, rle):

		if ptype == "closed":

			t = "Polygon_run"
			rt = "nvertices"

		elif ptype == "open":

			t = "PolygonCurve_run"
			rt = "nvertices"

		elif ptype == "face":

			t = "Polygon_run"
			rt = "nvertices_rle"

		else:

			t = "Polygon_run"
			rt = "nvertices_rle"

		primitives = [
			[
				[
					"type",t
				],
				[
					"startvertex",0,
					"nprimitives",nprims,
					rt,rle
				]
			]
		]

		self.vtx_count = nverts
		self.prim_count = nprims
		self.primitives = primitives

	# ----------------------------------------

	def setPrimGroups(self, pgrps_rle, grp_id):

		'''
		The prim groups funciton works by suppling a list of pairs (number and boolean)
		describing how all primitives relate to that specific group: So if the first 10 of 100
		primitives are within GROUP_1 that is supplied as [10, true, 90, false]. If the primitives
		20 to 40 are in GROUP_2 that is supplied as [20, false, 20, true, 60, false].
		'''

		pgrps = []

		# Structure the primitive groups relational (rle) list of pairs
		for i, prims in enumerate(pgrps_rle):

			if i == 0:

				pgrps.append([prims, True, sum(pgrps_rle[1:]), False])

			elif i == len(pgrps_rle) - 1:

				pgrps.append([sum(pgrps_rle[:-1]), False, prims, True])

			else:

				pgrps.append([sum(pgrps_rle[:i]), False, prims, True, sum(pgrps_rle[i + 1:]), False])

		# Write into the HouJSON groups structure
		for i, pgrp in enumerate(pgrps):

			grp_json = [
				[
					"name", "{}_{}".format(grp_id, i)
				],
				[
					"selection", [
						"unordered", [
							"boolRLE", pgrp
						]
					]
				]
			]

			self.prim_attribs.append(grp_json)

	# ----------------------------------------

	def setAttribs(self, attribs):

		if not isinstance(attribs, list):

			attribs = [attribs]

		for attrib in attribs:

			if attrib.getScope() == "point":

				self.pt_attribs.append(attrib.getJSON())

			elif attrib.getScope() == "vertex":

				self.vtx_attribs.append(attrib.getJSON())

			elif attrib.getScope() == "primitive":

				self.prim_attribs.append(attrib.getJSON())

			elif attrib.getScope() == "global":

				self.global_attribs.append(attrib.getJSON())

	# ----------------------------------------

	def setSpatialRef(self, centroid, cs="unknown"):

		centroid = list(centroid)

		if len(centroid) == 2:
			centroid.append(0.0)

		cs_attrib = ha.HouAttribute("sr_cs", "global", "string", cs)
		self.global_attribs.append(cs_attrib.getJSON())

		x_attrib = ha.HouAttribute("sr_cent_x", "global", "float", centroid[0])
		self.global_attribs.append(x_attrib.getJSON())

		y_attrib = ha.HouAttribute("sr_cent_y", "global", "float", centroid[2])
		self.global_attribs.append(y_attrib.getJSON())

		z_attrib = ha.HouAttribute("sr_cent_z", "global", "float", centroid[1])
		self.global_attribs.append(z_attrib.getJSON())

	# ----------------------------------------

	def getJSON(self):

		info = collections.OrderedDict()

		info["artist"] = "HAL9000"
		info["software"] = "FME"
		info["date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		info["hostname"] = socket.gethostname()
		info["bounds"] = self.bounds
		info["attribute_summary"] = "     {} point attributes:\tP\n".format(len(self.pt_attribs))

		geo = [
			"fileversion","18.0",
			"hasindex",False,
			"pointcount",self.pt_count,
			"vertexcount",self.vtx_count,
			"primitivecount",self.prim_count,
			"info",info,
			"topology",[
				"pointref",[
					"indices",self.indices
				]
			],
			"attributes",[
				"vertexattributes",self.vtx_attribs,
				"pointattributes",self.pt_attribs,
				"primitiveattributes",self.prim_attribs,
				"globalattributes",self.global_attribs,
			],
			"primitives",self.primitives,
			"pointgroups",self.pt_groups,
			"primitivegroups",self.prim_groups,
			"vertexgroups",self.vtx_groups,
			"edgegroups",self.edge_groups
		]

		return geo