import json
import os
import unittest
import logging
from ome_parser import OMEtoRDF

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

print(__location__)

from settings import Settings
settings=Settings()

dummy_api_url=os.environ.get('APP_HOST', "https://metadata.omero.matolab.org/api/")
dumy_url="https://omero.matolab.org/api/v0/m/images/"
dumy_image_url=dumy_url+"2"
dumy_rois_url=dumy_url+"2/rois/"


logging.basicConfig(level=logging.DEBUG)

class TestMain(unittest.TestCase):
    def test_image2(self):
        input_file='image2.json'
        output_file=input_file.split('.')[0]+".ttl"
        with open(os.path.join(__location__, 'tests', input_file)) as f:
            data = json.load(f)
        converter=OMEtoRDF(data,dumy_image_url)
        converter.annotate_prov(dummy_api_url+'image',settings)
        result=converter.to_rdf()
        result.serialize(format='turtle', destination='tests/'+output_file,auto_compact=True,indent=4)
        self.assertTrue(os.path.exists('tests/'+output_file))
    def test_rois2(self):
        input_file='rois2.json'
        output_file=input_file.split('.')[0]+".ttl"
        with open(os.path.join(__location__, 'tests', input_file)) as f:
            data = json.load(f)
        converter=OMEtoRDF(data,dumy_rois_url)
        converter.annotate_prov(dummy_api_url+'rois',settings)
        result=converter.to_rdf()
        result.serialize(format='turtle', destination='tests/'+output_file,auto_compact=True,indent=4)
        self.assertTrue(os.path.exists('tests/'+output_file))

    def test_rois83(self):
        input_file='rois83.json'
        output_file=input_file.split('.')[0]+".ttl"
        with open(os.path.join(__location__, 'tests', input_file)) as f:
            data = json.load(f)
        converter=OMEtoRDF(data,dumy_rois_url)
        converter.annotate_prov(dummy_api_url+'rois',settings)
        result=converter.to_rdf()
        result.serialize(format='turtle', destination='tests/'+output_file,auto_compact=True,indent=4)
        self.assertTrue(os.path.exists('tests/'+output_file))

if __name__ == '__main__':
    unittest.main()
