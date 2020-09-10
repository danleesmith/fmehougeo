import fme
import fmeobjects

import json, collections, itertools

# --------------------------------------------------------------------------

def lerp(vec1, vec2, fraction):

	'''
	Returns a point between vec1 and vec2 based on a weighted average
	given as a decimal fraction between 0 and 1
	'''

	clamped = max(min(fraction, 1.0), 0.0)
	inverse = 1.0 - clamped

	out = (
		(vec1[0] * clamped) + (vec2[0] * inverse), 
		(vec1[1] * clamped) + (vec2[1] * inverse)
		)

	return out

# --------------------------------------------------------------------------

def zuptoyup(vec):

	x = vec[0]
	y = vec[1]
	z = vec[2]

	return (x, z, y)

# --------------------------------------------------------------------------

class Attribute(object):

	def __init__(self, name, scope, atype, vals, special="not"):

		'''
		This attribute class creates attributes for all houdini
		geometry levels (scope) and for numeric and string data types.
		At this stage list (array) attribute types are not supported by the
		writer	
		'''

		# Attribute variables
		self.name = name
		self.scope = scope
		self.atype = atype
		self.values = vals
		self.indices = []

		self.defaults = None
		self.options = collections.OrderedDict()

		# Ensure values are provided as a nested list
		if not isinstance(self.values, list):

			self.values = [self.values]

		# Set attribute details
		if self.atype == "int":

			self.vtype = "numeric"
			self.vsize = 1
			self.storage = "int32"
			self.defaults = [0]

		elif self.atype == "float":

			self.vtype = "numeric"
			self.vsize = 1
			self.storage = "fpreal32"
			self.defaults = [0.0]

		elif self.atype == "vec2int":

			self.vtype = "numeric"
			self.vsize = 2
			self.storage = "int32"
			self.defaults = [0,0]

		elif self.atype == "vec2float":

			self.vtype = "numeric"
			self.vsize = 2
			self.storage = "fpreal32"
			self.defaults = [0.0,0.0]

		elif self.atype == "vec3int":

			self.vtype = "numeric"
			self.vsize = 3
			self.storage = "int32"
			self.defaults = [0,0,0]

		elif self.atype == "vec3float":

			self.vtype = "numeric"
			self.vsize = 3
			self.storage = "fpreal32"
			self.defaults = [0.0,0.0,0.0]

		elif self.atype == "vec4int":

			self.vtype = "numeric"
			self.vsize = 4
			self.storage = "int32"
			self.defaults = [0,0,0,0]

		elif self.atype == "vec4float":

			self.vtype = "numeric"
			self.vsize = 4
			self.storage = "fpreal32"
			self.defaults = [0.0,0.0,0.0,0.0]

		elif self.atype == "string":

			self.vtype = "string"
			self.vsize = 1
			self.storage = "int32"

			# Create the indices map for strings based on the
			# string grouping in the values
			self.values.sort()
			vkeys = [k for k, g in itertools.groupby(self.values)]

			for v in self.values:

				for i, key in enumerate(vkeys):

					if v == key:

						self.indices.append(i)

			self.values = vkeys

		# Set the attibute options and keywords
		if self.atype in ["vec2int", "vec2float", "vec3int", "vec3float","vec3int", "vec3float"]:

			if special == "ppos":

				self.options["type"] = collections.OrderedDict()
				self.options["type"]["type"] = "string"
				self.options["type"]["value"] = "point"

			elif special == "cartvector":

				self.options["type"] = collections.OrderedDict()
				self.options["type"]["type"] = "string"
				self.options["type"]["value"] = "vector"

			self.kword = "tuples"

		else:

			self.kword = "arrays"

		if self.scope == "detail" and self.vtype == "numeric":

			self.values = [self.values]

	# ----------------------------------------

	def getScope(self):

		return self.scope

	# ----------------------------------------

	def getJSON(self):

		# Create the JSON schema for the attributes data

		header = [
			"scope", "public",
			"type", self.vtype,
			"name", self.name,
			"options", self.options
		]

		value = [
			"size", self.vsize,
		]

		if self.defaults:

			value += [
				"defaults", [
					"size", self.vsize,
					"storage", "fpreal64",
					"values", self.defaults
				]
			]

		if self.vtype == "numeric":

			value += [ "storage", self.storage ]
			value += [
				"values", [
					"size", self.vsize,
					"storage", self.storage,
					self.kword, self.values
				]
			]

		elif self.vtype == "string":

			value += [
				"storage", self.storage,
				"strings", self.values,
				"indices", [
					"size", self.vsize,
					"storage", "int32",
					self.kword, [self.indices]
				]
			]

		else:

			value == self.values

		return [ header, value ]


# --------------------------------------------------------------------------

class Detail(object):

	'''
	A Detail object contains:
		- Point Attributes
		- Vertex Attributes
		- Primitive Attributes
		- Global/Detail Attributes
		- Group Information
		- A primitive map
	'''

	def __init__(self, pts, uvs, inds, pmap, np, bnds):

		self.points = pts
		self.uvcoords = uvs
		self.indices = inds
		self.primMap = pmap
		self.nprims = int(np)
		self.bounds = bnds

		self.pointAttribs = []
		self.vertAttribs = []
		self.primAttribs = []
		self.detailAttribs = []

		self.pointGroups = []
		self.vertexGroups = []
		self.primGroups = []

	# ----------------------------------------

	def setPoints(self):

		ptAttrib = Attribute("P", "point", "vec3float", self.points, special="ppos")
		self.pointAttribs.append(ptAttrib.getJSON())

	# ----------------------------------------

	def setUvcoords(self):

		uvAttrib = Attribute("uv", "vertex", "vec3float", self.uvcoords)
		self.vertAttribs.append(uvAttrib.getJSON())

	# ----------------------------------------


	def setAttrib(self, attrib):

		if attrib.getScope() == "point":

			self.pointAttribs.append(attrib.getJSON())

		elif attrib.getScope() == "vertex":

			self.vertAttribs.append(attrib.getJSON())

		elif attrib.getScope() == "primitive":

			self.primAttribs.append(attrib.getJSON())

		elif attrib.getScope() == "detail":

			self.detailAttribs.append(attrib.getJSON())

	# ----------------------------------------

	def setPrimGroups(self, pgrps_rle, model_id):

		'''
		The prim groups funciton works by suppling a list of pairs (number and boolean)
		describing how all primitives relate to that specific group so if the first 10 of 100
		primitives are within GROUP_1 that is supplied as [10, true, 90, false]. If the primitives
		20 to 40 are in GROUP_2 that is supplied as [20, false, 20, true, 60, false].
		'''

		primgroups = []

		for i, prims in enumerate(pgrps_rle):

			if i == 0:

				primgroups.append([prims, True, sum(pgrps_rle[1:]), False])

			elif i == len(pgrps_rle) - 1:

				primgroups.append([sum(pgrps_rle[:-1]), False, prims, True])

			else:

				primgroups.append([sum(pgrps_rle[:i]), False, prims, True, sum(pgrps_rle[i + 1:]), False])

		for i, pgrp in enumerate(primgroups):

			gjson = [
				[
					"name","struct_" + str(model_id) + "_m_" + str(i)
				],
				[
					"selection", [
						"unordered", [
							"boolRLE", pgrp
						]
					]
				]
			]

			self.primGroups.append(gjson)



	# ----------------------------------------

	def getJSON(self):

		'''
		Create the JSON schema for the detail object
		Currently only handles polygon mesh type objects
		'''

		flat_bounds = []

		for coords in self.bounds:
			for item in coords:
				flat_bounds.append(item)

		info = collections.OrderedDict()

		info["software"] = "FME"
		info["date"] = "Inset Date"
		info["hostname"] = "IT15942"
		info["artist"] = "dansmit"
		info["bounds"] = flat_bounds,
		info["primcount_summary"] = "          X Polygons\n"
		info["attribute_summary"] = "     X point attributes:\tP\n"

		data = [
			"fileversion","16.0.633",
			"hasindex",False,
			"pointcount",len(self.points),
			"vertexcount",len(self.indices),
			"primitivecount",self.nprims,
			"info",info,
			"topology",[
				"pointref",[
					"indices",self.indices
				]
			],
			"attributes",[
				"vertexattributes",self.vertAttribs,
				"pointattributes",self.pointAttribs,
				"primitiveattributes",self.primAttribs,
				"globalattributes",self.detailAttribs,
			],
			"primitives",[
				[
					[
						"type","Polygon_run"
					],
					[
						"startvertex",0,
						"nprimitives",self.nprims,
						"nvertices_rle",self.primMap
					]
				]
			],
			"primitivegroups",self.primGroups
		]

		return data


# --------------------------------------------------------------------------

class HouGeoWriter(object):

	def __init__(self):

		pass

	def input(self,feature):

		if feature.hasGeometry():

			'''
			Operating on FMEFeature
			'''

			# Get the feature's geometry
			geom = feature.getGeometry()

			if geom.isCollection():

				'''
				Operating on FMEMultiSurface (Geometry Container)
				This is the entire multipatch container and is the 
				equivalent of the Houdini Detail level
				'''

				# Get the planar centroid of the geometry
				bbx = geom.boundingBox()
				centroid = lerp(bbx[0], bbx[1], 0.5)

				# Offset the geometry to 0,0,0 cartesian
				offset = fmeobjects.FMEPoint(-centroid[0], -centroid[1], 0.0)
				geom.offset(offset)

				# Set the bounding volume of the geometry
				bounds = geom.boundingCube()

				# Create empties
				indices = []
				points = []
				uvcoords = []
				nverts = []
				primgroups = []

				# Track number of primitives
				primcount = 0

				for mesh in geom:

					'''
					Operating on FMEMesh
					This is the multipatch feature and is the
					eqivalent of Houdini Groups
					'''	

					# Get the number of primitives that comprise this mesh
					nprims = mesh.numParts()

					# Add the number of mesh primitives to the overall count
					primcount += nprims

					# Create the primitve group information with each entry being
					# the number of primtives in each group (these are always provided in order)
					primgroups.append(nprims)

					# Get the mesh verticies (points) and add them to the list
					verts = mesh.getVertices()
					points.extend(verts)

					# Keep tract of the point indices per mesh
					meshindices = []

					for part in mesh:

						'''
						Operating on FMEMeshPartIterator
						This is the multipatch 3D face and is the
						equivalent of a Houdini Primitive
						'''
						# Get the vertex indicies and drop the last entry
						vindices = part.getVertexIndices()[:-1]

						# Extend the indices by the primitive indicies
						meshindices.extend(vindices)

						# Insert the number of primitive vertices into list
						nverts.append(len(vindices))

						# Setup appearance/texture query
						try:

							# Get the appearance reference for the primitive (Material)
							matref = part.getAppearanceReference(True)
							mat = fmeobjects.FMELibrary().getAppearanceCopy(matref)

							# Get the texture for the material
							texref = mat.getTextureReference()
							tex = fmeobjects.FMELibrary().getTextureCopy(texref)

							# List the uvcoords based on the vertex indices
							partuvs = part.getTextureCoordinateIndices(True)

						except TypeError:

							partuvs = None

						# Check if there are uvcoordinates
						if partuvs is not None:

							for index in partuvs[:-1]:

								uvwq = mesh.getTextureCoordinateAt(index)
								u = uvwq[0]
								v = uvwq[1]

								uvcoords.append([u, v, 0.0])

						# Create default uvcoords if none exist
						else:

							for index in vindices:

								uvcoords.append([0.0, 0.0, 0.0])

					# Compile all discrete mesh indices per mesh into single list
					# for the whole feature geometry object
					if len(indices) > 0:

						indices.extend([(max(indices) + 1) + i for i in meshindices])

					else:

						indices.extend(meshindices)


				'''
				Create a number of vertices per primitive relational list of pairs (rle) 
				whereby the first value is the number of vertices per primitve and 
				the second value is the number of primitives that have this topology
				'''

				# Group the nverts list by number
				nvert_grps = []

				for n in nverts:
				
					if nvert_grps and nvert_grps[-1][0] == n:

						nvert_grps[-1].append(n)

					else:

						nvert_grps.append([n])

				# Create the primitives relational list
				nvertices_rle = []

				for grp in nvert_grps:

					nvertices_rle.extend([grp[0], len(grp)])

				# Reorient coordinates to yup
				bounds = [zuptoyup(bound) for bound in bounds]
				points = [zuptoyup(point) for point in points]

				# Get Strucutre ID
				struct_id = feature.getAttribute("STRUCT_ID")

				# Create detail object
				geo_detail = Detail(points, uvcoords, indices, nvertices_rle, primcount, bounds)
				geo_detail.setPoints()
				geo_detail.setUvcoords()
				geo_detail.setPrimGroups(primgroups, struct_id)
	
				# Get and set the feature attributes
				for aname in feature.getAllAttributeNames():

					aval = feature.getAttribute(aname)
					atype = feature.getAttributeType(aname)
					
					if atype in [2,3,4,5,6,7,13,14]: # Value is an integer

						# Handle Nulls
						if aval is None:

							aval = 0

						geo_detail.setAttrib( Attribute(aname, "detail", "int", aval) )

					elif atype in [8,9,10]: # Value is a float

						# Handle Nulls
						if aval is None:

							aval = 0.0

						geo_detail.setAttrib( Attribute(aname, "detail", "float", aval) )

					elif atype in [11,12]: # Value is a string

						# Handle Nulls
						if aval is None:

							aval = ""

						geo_detail.setAttrib( Attribute(aname, "detail", "string", aval) )


				# Set HOU JSON as an attribute on the feature
				feature.setAttribute("_hou_json", json.dumps(geo_detail.getJSON(), separators=(',', ':'), indent=None))

				# Output the feature
				self.pyoutput(feature)

	def close(self):

		pass