# --------------------------------------------------------------------------
# Imports
# --------------------------------------------------------------------------

import collections

# --------------------------------------------------------------------------
# Classes
# --------------------------------------------------------------------------

'''
This class creates attributes for all houdini geometry levels (scope) and for 
numeric and string data types. At this stage list (array) attribute types are 
not supported by the writer	
'''

class HouAttribute(object):

	def __init__(self, name, scope, atype, vals, special="not"):

		# Attribute variables
		self.name = name
		self.scope = scope
		self.atype = atype
		self.values = vals

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

	# ----------------------------------------

	def getScope(self):

		return self.scope

	# ----------------------------------------

	def getName(self):

		return self.name

	# ----------------------------------------

	def getValues(self):

		return self.values

	# ----------------------------------------

	def setFirstValue(self, val):

		self.values = [val]

	# ----------------------------------------

	def appendValue(self, val):

		self.values.append(val)


	# ----------------------------------------

	def overwriteValues(self, vals):

		if not isinstance(vals, list):

			self.values = [vals]

		else:

			self.values = vals

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
			"storage", self.storage,
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
			
			if self.kword == "tuples":

				value += [
					"values", [
						"size", self.vsize,
						"storage", self.storage,
						self.kword, self.values
					]
				]

			else:

				value += [
					"values", [
						"size", self.vsize,
						"storage", self.storage,
						self.kword, [self.values]
					]
				]

		elif self.vtype == "string":

			value += [
				"strings", self.values,
				"indices", [
					"size", self.vsize,
					"storage", "int32",
					self.kword, [[i for i in range(len(self.values))]] # Indices
				]
			]

		else:

			value == self.values

		return [ header, value ]