# -*- coding: utf-8 -*-
from typing import Tuple

from errno import ESTALE
from rdflib import BNode, URIRef, Literal, Graph, Namespace
from rdflib.util import guess_format
from rdflib.namespace import OWL, RDF, XSD, RDFS, PROV

from re import sub
import ast
from dateutil.parser import parse as date_parse
from datetime import datetime
from pydantic import BaseSettings

OME_SOURCE = './ome.ttl'
OME_SOURCE_URL="https://github.com/Mat-O-Lab/OmeroExtractor/raw/main/ome.xml"
OME = Namespace(OME_SOURCE_URL+"#")
OA = Namespace("http://www.w3.org/ns/oa#")
QUDT = Namespace("http://qudt.org/schema/qudt/")

key_original_meta='original_meta'

ome_graph = Graph()
ome_graph.parse(OME_SOURCE, format='turtle')



def is_date(string, fuzzy=False)->bool:
    try:
        date_parse(string, fuzzy=fuzzy)
        return True

    except ValueError:
        return False
    
def snake_case(s):
  return '_'.join(
    sub('([A-Z][a-z]+)', r' \1',
    sub('([A-Z]+)', r' \1',
    s.replace('-', ' '))).split()).lower()

UMLAUTE = {
            '\u00e4': 'ae',  # U+00E4	   \xc3\xa4
            '\u00f6': 'oe',  # U+00F6	   \xc3\xb6
            '\u00fc': 'ue',  # U+00FC	   \xc3\xbc
            '\u00c4': 'Ae',  # U+00C4	   \xc3\x84
            '\u00d6': 'Oe',  # U+00D6	   \xc3\x96
            '\u00dc': 'Ue',  # U+00DC	   \xc3\x9c
            '\u00df': 'ss',  # U+00DF	   \xc3\x9f
        }

def make_id(string)-> str:
    for k in UMLAUTE.keys():
        string = string.replace(k, UMLAUTE[k])
    else:
        return sub('[^A-ZÜÖÄa-z0-9]+', '', string.title().replace(" ", ""))

def create_note(graph: Graph, label: str, value):
    entity=URIRef(make_id(label))
    graph.add((entity,RDF.type,OA.Annotation))
    graph.add((entity,RDFS.label,Literal(label)))
    return entity

def get_value_type(string: str)-> Tuple:
    string = str(string)
    # remove spaces and replace , with . and
    string = string.strip().replace(',', '.')
    if len(string) == 0:
        return 'BLANK', None
    try:
        t = ast.literal_eval(string)
    except ValueError:
        return 'TEXT', XSD.string
    except SyntaxError:
        if is_date(string):
            return 'DATE', XSD.dateTime
        else:
            return 'TEXT', XSD.string
    else:
        if type(t) in [int, float, bool]:
            if type(t) is int:
                return 'INT', XSD.integer
            if t in set((True, False)):
                return 'BOOL', XSD.boolean
            if type(t) is float:
                return 'FLOAT', XSD.double
        else:
            #return 'TEXT'
            return 'TEXT', XSD.string
        
def describe_value(graph, node, value_string: str):
    #remove leading and trailing white spaces
    # if pd.isna(value_string):
    #     return {}
    
    val_type=get_value_type(value_string)
    if val_type:
        body=BNode()
        graph.add((node,OA.hasBody,body))
    
    if val_type[0] == 'INT':
        graph.add((body,RDF.type,QUDT.QuantityValue))
        graph.add((body,QUDT.value,Literal(int(value_string),datatype=val_type[1])))
    elif val_type[0] == 'BOOL':
        graph.add((body,RDF.type,QUDT.QuantityValue))
        graph.add((body,QUDT.value,Literal(bool(value_string),datatype=val_type[1])))
    elif val_type[0] == 'FLOAT':
        if isinstance(value_string,str):
            #replace , with . as decimal separator
            value_string = value_string.strip().replace(',', '.')
        graph.add((body,RDF.type,QUDT.QuantityValue))
        graph.add((body,QUDT.value,Literal(float(value_string),datatype=val_type[1])))
    elif val_type[0] == 'DATE':
        print(value_string)
        graph.add((body,RDF.type,QUDT.QuantityValue))
        graph.add((body,QUDT.value,Literal(str(date_parse(value_string).isoformat()),datatype=val_type[1])))
    else:
        graph.add((body,RDF.type,QUDT.TextualBody))
        graph.add((body,OA.purpose,OA.tagging))
        graph.add((body,QUDT.value,Literal(value_string.strip(),datatype=val_type[1])))
def get_entity_type(string: str):
    hits = list(ome_graph[:OME.ome_type:Literal(string)])
    if hits:
        return hits[0]
    else:
        return None

class OMEtoRDF:
    """Class for Converting OME meta data json to RDF with help of OME Ontology.
    """
    def __init__(self,json_dict: dict={}, root_url: str='', api_endpoint: str='') -> None:
        #print(json_dict.keys())
        self.data=json_dict#.get('data',None)
        self.root=URIRef(root_url)
        print(api_endpoint)
        self.graph=Graph()
        self.graph.bind('ome',OME)
        self.graph.bind('qudt',QUDT)
        self.graph.bind('prov',PROV)
        
        #print(list(ome_graph[: RDF.type:]))

    def annotate_prov(self, api_url: str, settings: BaseSettings):
        print('adding prov-o meta')
        activity=URIRef(api_url)
        release=URIRef(settings.source+"/releases/tag/"+settings.version)
        self.graph.add((self.root,PROV.wasGeneratedBy,activity))
        self.graph.add((activity,RDF.type,PROV.Activity))
        self.graph.add((activity,PROV.wasAssociatedWith,release))
        self.graph.add((release,RDF.type,PROV.SoftwareAgent))
        self.graph.add((release,RDFS.label,Literal(settings.app_name+settings.version)))
        self.graph.add((release,PROV.hadPrimarySource,Literal(settings.source)))
        
        self.graph.add((self.root,PROV.generatedAtTime,Literal(str(datetime.now().isoformat()), datatype=XSD.dateTime)))
        
        # return {
        #     "prov:wasGeneratedBy": {
        #         "@id": api_url,
        #         "@type": "prov:Activity",
        #         "prov:wasAssociatedWith":  {
        #             "@id": "https://github.com/Mat-O-Lab/CSVToCSVW/releases/tag/"+settings.version,
        #             "rdfs:label": settings.app_name+settings.version,
        #             "prov:hadPrimarySource": settings.source,
        #             "@type": "prov:SoftwareAgent"
        #         }
        #     },
        #     "prov:generatedAtTime": {
        #             "@value": str(datetime.now().isoformat()),
        #             "@type": "xsd:dateTime"
        #         }
        #     }

        
    def to_rdf(self,anonymize=True):
        print('start mapping2\n\n\n\n\n\n')
        #result.bind('data', _get_ns(base_url))        
        iterate_json(self.data, self.graph,base_url=self.root)
        self.graph = fix_iris(self.graph, base_url=self.root)
        if anonymize:
            [self.graph.remove((subject, None, None)) for subject in self.graph.subjects(RDF.type, OME.User)]
        return self.graph


def iterate_json(data, graph, last_entity=None, relation=None, base_url=None):
    if isinstance(data, dict):
        # lookup if the id and type in dict result in a ontology entity
        entity, e_class, parent = create_instance_triple(data, uri=base_url)
        #print(entity,e_class,parent)
        if entity and e_class:
            # if the entity is a Identifier, only create it if it relates to entity previously created
            print('create entity: {} {}'.format(entity,e_class))
            print('last entity: {} {}'.format(last_entity,relation))
            graph.add((entity, RDF.type, e_class))
            if last_entity and relation:
                #print('create relation: {} {} {}'.format(last_entity,relation,entity))
                graph.add((last_entity, relation, entity))
            else:
                print('missing relation: {} {} {} {}'.format(last_entity,e_class,relation,entity))
            for key, value in data.items():
                if key in ["@type", "@id"]:
                    #alrady handled
                    continue
                relation = get_entity_type(key)
                #print("key: {}".format(key),"relation: {}".format(relation))
                # if the key is properties all json keys in that dict are relations to openbis properties followed by there values
                    
                if isinstance(value, dict):
                    if key=="original_meta":
                        meta_node, e_class, parent = create_instance_triple(value)
                        graph.add((meta_node, RDF.type, e_class))
                        for s, d in value.items():
                            if isinstance(d,dict):
                                for k,v in d.items():
                                    prop_name=snake_case('{} {}'.format(s,k))
                                    #print(prop_name,v)
                                    #graph.add((meta_node, OME.notes, Literal(v)))
                                    note=create_note(graph,'{} {}'.format(s,k),v)
                                    describe_value(graph, note, v)
                                    graph.add((meta_node, OME.notes, note))
                        graph.add((entity, relation, meta_node))
                    else:               
                        #print('a dict at {} calling iterate_json with: {} {}'.format(key,entity,relation) )
                        # recursively inter over all json objects
                        iterate_json(value, graph, last_entity=entity, relation=relation)
                        # add the ObjectProperty to the created instance
                        
                elif isinstance(value, list):
                    #print('a list at {} calling iterate_json with: {} {}'.format(key,entity,relation) )
                    # recursively inter over all json objects
                    iterate_json(value, graph, last_entity=entity, relation=relation)
                    # see if an entity is created and relate it if necessary
                else:
                    # if its no dict or list test if its kind of object/data/annotation property and set it
                    if (value or isinstance(value,bool)) and relation:
                        graph.add((entity, relation, Literal(value)))
                    elif not relation:
                        print('missing relation to Literal: {} {} {}'.format(entity,relation,value))
            
    elif isinstance(data, list):
        for item in data:
            iterate_json(item, graph, last_entity=last_entity, relation=relation)


def replace_iris(old: URIRef, new: URIRef, graph: Graph):
    # replaces all iri of all triple in a graph with the value of relation
    old_triples = list(graph[old: None: None])
    for triple in old_triples:
        graph.remove((old, triple[0], triple[1]))
        graph.add((new, triple[0], triple[1]))
    old_triples = list(graph[None: None: old])
    for triple in old_triples:
        graph.remove((triple[0], triple[1], old))
        graph.add((triple[0], triple[1], new))
    old_triples = list(graph[None: old: None])
    for triple in old_triples:
        graph.remove((triple[0], old, triple[1]))
        graph.add((triple[0], new, triple[1]))


def fix_iris(graph, base_url=None):
    #replace int iris with permids if possible
    # for permid in graph[: RDF.type: OBIS.PermanentIdentifier]:
    #     permid_value = graph.value(permid, RDF.value)
    #     identifies = graph.value(permid, OBIS.is_identifier_of)
    #     identifies_type = graph.value(identifies, RDF.type)
    #     type_str = identifies_type.split('/')[-1].lower()
    #     #print(identifies,identifies_type)
    #     if identifies_type in [OWL.Class]:
    #         type_str='class'
    #     elif identifies_type in [OWL.ObjectProperty]:
    #         type_str='object_property'
    #     graph.bind(type_str,_get_ns(base_url)[f'{type_str}/'])
    #     new = URIRef(f'{type_str}/{permid_value}',_get_ns(base_url))
    #     replace_iris(identifies, new, graph)
    #     #print(identifies,new)

    # replace iri of created object properties with value of code if possible
    # for property in graph[: RDF.type: OWL.ObjectProperty]:
    #     code_value = graph.value(property, OBIS.code)
    #     if code_value:
    #         new = _get_ns(base_url)[code_value]
    #         replace_iris(property, new, graph)

    # for identifier in graph[: RDF.type: OBIS.Identifier]:
    #     replace_iris(identifier, BNode(), graph)
    # for identifier in graph[: RDF.type: OBIS.PermanentIdentifier]:
    #     replace_iris(identifier, BNode(), graph)
    return graph

def create_instance_triple(data: dict, uri= None):
    entity=None
    o_class=None
    parent=None
    #print( data.keys())
    if all(prop in data.keys() for prop in ['@type']):
        o_class = get_entity_type(data['@type'])
        if o_class:
            #entity=URIRef(instance_id, TEMP)
            if uri:
                entity=uri
            else:
                entity=BNode()
        # if data['@type']=='as.dto.sample.SampleType':
        #     parent=OBIS.Object
        # elif data['@type']=='as.dto.experiment.ExperimentType':
        #     parent=OBIS.Collection
    return entity, o_class, parent
