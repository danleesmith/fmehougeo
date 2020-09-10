import fme, fmeobjects, json
from fmehougeo import attrib as ha
from fmehougeo import geo as hg

# --------------------------------------------------------------------------
# Vector Functions
# --------------------------------------------------------------------------

'''
Returns a point between vec1 and vec2 based on a weighted average
given as a decimal fraction between 0 and 1
'''

def lerp(vec1, vec2, fraction):

	clamped = max(min(fraction, 1.0), 0.0)
	inverse = 1.0 - clamped

	out = (
		(vec1[0] * clamped) + (vec2[0] * inverse), 
		(vec1[1] * clamped) + (vec2[1] * inverse)
		)

	return out

# --------------------------------------------------------------------------

def swizzleYZ(vec):

	x = vec[0]
	y = vec[1]
	z = vec[2]

	return (x, z, -y)

# --------------------------------------------------------------------------
# Centroid and Bounding Box Functions
# --------------------------------------------------------------------------

def getCentroid(geom):

	# Get the planar centroid of the geometry
	bbx = geom.boundingBox()
	centroid = lerp(bbx[0], bbx[1], 0.5)

	# Return the centroid
	return centroid

def setBounds(offset, bbx):

	# Get and set the minimum point of the offset bounding box
	xyz =  bbx.getLocalMinPointXYZ()
	bbxmin = fmeobjects.FMEPoint(xyz[0], xyz[1], xyz[2])
	bbxmin.offset(offset)

	# Get and set the maximum point of the offset bounding box
	xyz =  bbx.getLocalMaxPointXYZ()
	bbxmax = fmeobjects.FMEPoint(xyz[0], xyz[1], xyz[2])
	bbxmax.offset(offset)

	# Return the bounds
	return list(swizzleYZ(bbxmin.getXYZ()) + swizzleYZ(bbxmax.getXYZ()))

# --------------------------------------------------------------------------
# Attribute Functions
# --------------------------------------------------------------------------

'''
The following functions will only handle FME attributes that are prefixed with 
'attrib_'. This has been done to enfore good attribute management and ensure 
that all non-exposed/inbuilt attributes from FME are ignored.
'''

def createHouAttribs(feature, scope):
	
	attribs = []

	for attrib_name in feature.getAllAttributeNames():

		if attrib_name.startswith("attrib_"):

			aname = attrib_name[7:]
			atype = feature.getAttributeType(attrib_name)

			if atype in [2,3,4,5,6,7,13,14]: # Value is an integer

				attribs.append(ha.HouAttribute(aname, scope, "int", 0))

			elif atype in [8,9,10]: # Value is a float

				attribs.append(ha.HouAttribute(aname, scope, "float", 0.0))

			elif atype in [11,12]: # Value is a string

				attribs.append(ha.HouAttribute(aname, scope, "string", ""))

	return attribs

# --------------------------------------------------------------------------

def writeHouAttribs(feature_index, feature, attribs):

	for attrib_name in feature.getAllAttributeNames():

		for attrib in attribs:

			if "attrib_" + attrib.getName() == attrib_name:
				
				val = feature.getAttribute(attrib_name)

				if feature_index == 1:

					attrib.setFirstValue(val)

				else:

					attrib.appendValue(val)

	return attribs

# --------------------------------------------------------------------------
# FME Feature Conversion Functions
# --------------------------------------------------------------------------

'''
This function will ONLY operate on FMEMesh and FMEMultiSurface inputs. Please
ensure that the geometry is supplied to the PythonCaller in either of these formats.
'''

def processFMESurface(feature):

	nfaces = 0
	nverts = []
	vtxpool = []
	indices = []

	'''
	Operate on singular FMEFeature
	'''   

	if feature.hasGeometry():

		# Get the feature's geometry
		geom = feature.getGeometry()

		# Set the offset
		centroid = getCentroid(geom)
		offset = fmeobjects.FMEPoint(-centroid[0], -centroid[1], 0.0)

		# Set the offset bounds of the geometry
		bounds = setBounds(offset, fmeobjects.FMEBox((
			geom.boundingCube()[0][0],
			geom.boundingCube()[0][1],
			geom.boundingCube()[0][2],
			geom.boundingCube()[1][0],
			geom.boundingCube()[1][1],
			geom.boundingCube()[1][2]
		)))

		# Check it the geometry is and FMEMesh object
		if isinstance(geom, fmeobjects.FMEMesh):

			mesh = geom

			'''
			Operating on FMEMesh
			'''

			# Get the number of faces that comprise this mesh and track
			nfaces += mesh.numParts()

			# track number of vertices per face
			vtxpool.extend(mesh.getVertices())

			# Keep track of the vertex indices mapping per mesh
			meshindices = []
			
			for face in mesh:

				'''
				Operating on FMEFace
				'''

				# Get the vertex indices for the face and drop the last entry
				vindices = face.getVertexIndices()[:-1]

				# Extend the mesh indices per face
				meshindices.extend(vindices)

				# Insert the number of vertices per face into the list
				nverts.append(len(vindices))

			# Compile and insert the vertex indices back into the overall indices
			if len(indices) > 0:

				indices.extend([(max(indices) + 1) + i for i in meshindices])

			else:

				indices.extend(meshindices)

		# Check if the geometry is an FMEMultiSurface object (a colleciton of FMEMeshes)
		elif isinstance(geom, fmeobjects.FMEMultiSurface):

			'''
			Operating on FMEMultiSurface
			'''

			for mesh in geom:

				'''
				Operating on FMEMesh
				'''
				nfaces += mesh.numParts()
				vtxpool.extend(mesh.getVertices())
				meshindices = []

				for face in mesh:

					'''
					Operating on FMEFace
					'''
					vindices = face.getVertexIndices()[:-1]
					meshindices.extend(vindices)
					nverts.append(len(vindices))

				if len(indices) > 0:

					indices.extend([(max(indices) + 1) + i for i in meshindices])

				else:

					indices.extend(meshindices)

		else:

			print("ERROR: Please coerce the geometry into the FMEMesh or FMEMultiSurface format")

		'''
		The next two blocks create a number of vertices per primitive relational list of 
		pairs (rle) whereby the first value is the number of vertices per primitve and 
		the second value is the number of primitives that have this topology
		'''

		# Group the nverts list by number
		nvert_grps = []

		for n in nverts:
		
			if nvert_grps and nvert_grps[-1][0] == n:

				nvert_grps[-1].append(n)

			else:

				nvert_grps.append([n])

		# Create the vertex/primitives relational list
		rle = []

		for grp in nvert_grps:

			rle.extend([grp[0], len(grp)])

		# Convert the vertices back into FMEPoint objects and offset accordingly
		points = []

		for point in [fmeobjects.FMEPoint(vtx[0], vtx[1], vtx[2]) for vtx in vtxpool]:

			point.offset(offset)
			points.append(swizzleYZ(point.getXYZ()))

		# Create Houdini .geo string
		hougeo = hg.HouGeo(bounds)
		hougeo.setPoints(points)
		hougeo.setIndices(indices)
		hougeo.setPrimitives("face", nfaces, sum(nverts), rle)
		hougeo.setSpatialRef(centroid, cs=feature.getCoordSys())

		# Write attributes to .geo
		detail_attribs = createHouAttribs(feature, "global")
		detail_attribs = writeHouAttribs(1, feature, detail_attribs)
		hougeo.setAttribs(detail_attribs)

		# Return .geo string
		return json.dumps(hougeo.getJSON(), separators=(',',':'), indent=None)

# --------------------------------------------------------------------------

'''
This function will ONLY operate on FMEPoint features. It will not ingest Muti Point
features, these must be deagregated before feeding into this function.
'''

def processFMEPoints(features, centroid, offset, bounds):

	npoints = 0
	points = []

	'''
	Operate array of FMEFeatures
	''' 
	
	# Create .geo attribute template from first feature
	point_attribs = createHouAttribs(features[0], "point")

	# Loop through features
	for feature in features:

		'''
		Operate singular on FMEFeature
		''' 

		# Get the FMEPoint
		point = feature.getGeometry()
		point.offset(offset)
		points.append(swizzleYZ(point.getXYZ()))

		# Increment point number
		npoints += 1

		# Write attributes for this point only
		point_attribs = writeHouAttribs(npoints, feature, point_attribs)

	# Create Houdini .geo string
	hougeo = hg.HouGeo(bounds)
	hougeo.setPoints(points)
	hougeo.setSpatialRef(centroid, cs=feature.getCoordSys())

	# Write attributes to .geo
	hougeo.setAttribs(point_attribs)

	# Return .geo string
	return json.dumps(hougeo.getJSON(), separators=(',',':'), indent=None)

# --------------------------------------------------------------------------

'''
This function will ONLY operate on FMECurve features. It will not ingest Muti Curve
features, these must be deagregated before feeding into this function.
'''

def processFMELines(features, centroid, offset, bounds):

	nprims = 0
	points = []
	prim_run = []
	
	'''
	Operate array of FMEFeatures
	''' 
	
	# Create .geo attribute template from first feature
	prim_attribs = createHouAttribs(features[0], "primitive")

	# Loop through features
	for feature in features:

		'''
		Operate singular on FMEFeature
		''' 

		# Get the feature geometry as an FMELine
		this_line = feature.getGeometry().getAsLine()

		# Get the list of FMEPoints
		this_points = this_line.getPoints()

		# Offset and append points
		for point in this_points:

			# Get the FMEPoint
			point.offset(offset)
			points.append(swizzleYZ(point.getXYZ()))

		# Keep track of the amount of points per line
		prim_run.append(len(this_points))

		# Keep track of the number of lines
		nprims += 1

		# Write the attributes
		prim_attribs = writeHouAttribs(nprims, feature, prim_attribs)

	# Create Houdini .geo string
	hougeo = hg.HouGeo(bounds)
	hougeo.setPoints(points)
	hougeo.setIndices([i for i in range(len(points))])
	hougeo.setPrimitives("open", nprims, len(points), prim_run)
	hougeo.setSpatialRef(centroid, cs=feature.getCoordSys())

	# Write attributes to .geo
	hougeo.setAttribs(prim_attribs)

	# Return .geo string
	return json.dumps(hougeo.getJSON(), separators=(',',':'), indent=None)

# --------------------------------------------------------------------------

'''
This function will ONLY operate on FMEArea features. It will not ingest Muti Area
features, these must be deagregated before feeding into this function. Also this function
also requires that polygon holes (donuts) are also pre-processed with an additional ptype
(shell or hole) attribute to provide the best results.
'''

def processFMEAreas(features, centroid, offset, bounds):

	nprims = 0
	points = []
	prim_run = []
	
	'''
	Operate array of FMEFeatures
	''' 
	
	# Create .geo attribute template from first feature
	prim_attribs = createHouAttribs(features[0], "primitive")

	# Loop through features
	for feature in features:

		'''
		Operate singular on FMEFeature
		''' 

		# Get the feature geometry of as an FMEArea
		this_area = feature.getGeometry()
		
		# Get the boundary of the area as an FMELine
		this_boundary = this_area.getBoundaryAsCurve().getAsLine()

		# Get the list of FMEPoints (dropping the last point because it is a duplicate)
		this_points = this_boundary.getPoints()[:-1]

		# Offset and append points
		for point in this_points:

			# Get the FMEPoint
			point.offset(offset)
			points.append(swizzleYZ(point.getXYZ()))

		# Keep track of the amount of points per line
		prim_run.append(len(this_points))

		# Keep track of the number of areas
		nprims += 1

		# Write the attributes
		prim_attribs = writeHouAttribs(nprims, feature, prim_attribs)

	# Create Houdini .geo string
	hougeo = hg.HouGeo(bounds)
	hougeo.setPoints(points)
	hougeo.setIndices([i for i in range(len(points))])
	hougeo.setPrimitives("closed", nprims, len(points), prim_run)
	hougeo.setSpatialRef(centroid, cs=feature.getCoordSys())

	# Write attributes to .geo
	hougeo.setAttribs(prim_attribs)

	# Return .geo string
	return json.dumps(hougeo.getJSON(), separators=(',',':'), indent=None)