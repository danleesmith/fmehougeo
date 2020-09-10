# fmehougeo
This python library has beeen specifically for use with [FME](https://www.safe.com/fme/). Due to dependencies on the FME Python API it will not work in general applictions.

The main purpose of this library is to convert from FMEFeature objects into a json string that matches the [Houdini](https://www.sidefx.com/) .geo format.

The *HoudiniGeoWriter.py* file contained in the root of the main repository is example code of how this library can be used within an FME PythonCaller transformer. The *HoudiniGeoWriter.fmx* is a FME CustomTransformer that makes use of this integration.