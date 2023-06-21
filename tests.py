import json
import os
import unittest

from ome_parser import OMEtoRDF

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

print(__location__)

dummy_api_url="https://metadata.omero.matolab.org/api/imagemeta"

from settings import Settings

settings=Settings()

class TestMain(unittest.TestCase):
    def test_image(self):
        input_file='sample1.json'
        output_file=input_file.split('.')[0]+".ttl"
        with open(os.path.join(__location__, 'tests', input_file)) as f:
            data = json.load(f)
        converter=OMEtoRDF(data,'http://example.com')
        converter.annotate_prov(dummy_api_url,settings)
        result=converter.to_rdf()
        result.serialize(format='turtle', destination='tests/'+output_file,auto_compact=True,indent=4)
        self.assertTrue(os.path.exists('tests/'+output_file))
    def test_image2(self):
        input_file='sample86.json'
        output_file=input_file.split('.')[0]+".ttl"
        with open(os.path.join(__location__, 'tests', input_file)) as f:
            data = json.load(f)
        converter=OMEtoRDF(data,'http://example.com')
        result=converter.to_rdf()
        result.serialize(format='turtle', destination='tests/'+output_file,auto_compact=True,indent=4)
        self.assertTrue(os.path.exists('tests/'+output_file))
    def test_image3(self):
        input_file='sample92.json'
        output_file=input_file.split('.')[0]+".ttl"
        with open(os.path.join(__location__, 'tests', input_file)) as f:
            data = json.load(f)
        converter=OMEtoRDF(data,'http://example.com')
        result=converter.to_rdf()
        result.serialize(format='turtle', destination='tests/'+output_file,auto_compact=True,indent=4)
        self.assertTrue(os.path.exists('tests/'+output_file))
    
if __name__ == '__main__':
    unittest.main()
