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

import logging

OME_SOURCE = './ome.ttl'
OME_SOURCE_URL="https://github.com/Mat-O-Lab/OmeroExtractor/raw/main/ome.ttl"
OME = Namespace(OME_SOURCE_URL+"#")
OA = Namespace("http://www.w3.org/ns/oa#")
QUDT = Namespace("http://qudt.org/schema/qudt/")

key_original_meta='original_meta'

ome_graph = Graph()
ome_graph.parse(OME_SOURCE, format='turtle')



def get_hex_color(i:int):
    R = (i & 0x000000FF)
    G = (i & 0x0000FF00) >> 8
    B = (i & 0x00FF0000) >> 16
    A = (i & 0xFF000000) >> 24
    hex_code = f"#{R:02x}{G:02x}{B:02x}"
    return hex_code



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
    if val_type[0] == 'INT':
        body=BNode()
        graph.add((node,OA.hasBody,body))
        graph.add((body,RDF.type,QUDT.QuantityValue))
        graph.add((body,QUDT.value,Literal(int(value_string),datatype=val_type[1])))
    elif val_type[0] == 'BOOL':
        body=BNode()
        graph.add((node,OA.hasBody,body))
        graph.add((body,RDF.type,QUDT.QuantityValue))
        graph.add((body,QUDT.value,Literal(bool(value_string),datatype=val_type[1])))
    elif val_type[0] == 'FLOAT':
        if isinstance(value_string,str):
            #replace , with . as decimal separator
            value_string = value_string.strip().replace(',', '.')
        body=BNode()
        graph.add((node,OA.hasBody,body))
        graph.add((body,RDF.type,QUDT.QuantityValue))
        graph.add((body,QUDT.value,Literal(float(value_string),datatype=val_type[1])))
    elif val_type[0] == 'DATE':
        body=BNode()
        graph.add((node,OA.hasBody,body))
        graph.add((body,RDF.type,QUDT.QuantityValue))
        graph.add((body,QUDT.value,Literal(str(date_parse(value_string).isoformat()),datatype=val_type[1])))
    else:
        graph.add((node,OA.hasLiteralBody,Literal(value_string.strip(),datatype=val_type[1])))
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
        self.url=root_url
        logging.debug(self.url)
        self.root=URIRef("")
        logging.debug(api_endpoint)
        self.graph=Graph()
        self.graph.add((self.root,OME.rawMeta,Literal(self.url,datatype=XSD.anyURI)))
        
        self.image_id=self.url.rsplit('/',1)[-1]
        self.host=self.url.rsplit('/api',1)[0]
        
        self.graph.bind('ome',OME)
        self.graph.bind('qudt',QUDT)
        self.graph.bind('prov',PROV)
        self.graph.bind('oa',OA)
        #print(list(ome_graph[: RDF.type:]))

    def annotate_prov(self, api_url: str, settings: BaseSettings):
        logging.debug('adding prov-o meta')
        activity=URIRef(api_url)
        release=URIRef(settings.source+"/releases/tag/"+settings.version)
        self.graph.add((self.root,PROV.wasGeneratedBy,activity))
        self.graph.add((activity,RDF.type,PROV.Activity))
        self.graph.add((activity,PROV.wasAssociatedWith,release))
        self.graph.add((release,RDF.type,PROV.SoftwareAgent))
        self.graph.add((release,RDFS.label,Literal(settings.app_name+settings.version)))
        self.graph.add((release,PROV.hadPrimarySource,Literal(settings.source)))
        
        self.graph.add((self.root,PROV.generatedAtTime,Literal(str(datetime.now().isoformat()), datatype=XSD.dateTime)))
    
    def fix_data(self):
        logging.debug("proxying links")
        call_url=list(self.graph.subjects(RDF.type,PROV.Activity))[0]
        for image, rois in self.graph[None: OME.rois: None]:
            self.graph.remove((image, OME.rois, rois))
            rois_url=call_url.split('/api',1)[0]+"/api/rois/"+self.image_id
            new_rois=URIRef(rois_url)
            self.graph.add((image, OME.rois, new_rois))
            logging.debug("replaced {} with {}".format(rois,new_rois))
        logging.debug("fix colors")
        for predicate in [OME.strokeColor,OME.fillColor]:
            for object, color in self.graph.subject_objects(predicate):
                new_color=Literal(get_hex_color(int(color)))
                self.graph.remove((object, predicate, color))
                self.graph.add((object, predicate, new_color))
            
        

        
    def to_rdf(self,anonymize=True):
        logging.debug('start mapping')
        #result.bind('data', _get_ns(base_url))        
        iterate_json(self.data, self.graph,base_url=self.root)
        #add download urls
        for image in self.graph.subjects(RDF.type, OME.Image):
            self.graph.add((image,OME.download,Literal(self.host+"/webgateway/archived_files/download/"+self.image_id,datatype=XSD.anyURI)))
            # add render url
            render_url=self.host+"/webgateway/render_image/"+self.image_id
            self.graph.add((self.root,OME.url,Literal(render_url,datatype=XSD.anyURI)))
        
        self.fix_data()
        if anonymize:
            [self.graph.remove((subject, None, None)) for subject in self.graph.subjects(RDF.type, OME.User)]
        return self.graph


def iterate_json(data, graph, last_entity=None, relation=None, base_url=None):
    logging.debug('next iteration')
    if isinstance(base_url,(URIRef,BNode)):
        logging.debug('base_url is set to: {}'.format(base_url))            
    if isinstance(data, dict):
        logging.debug("keys:"+str(data.keys()))
        # lookup if the id and type in dict result in a ontology entity
        entity, e_class, parent = create_instance_triple(data, uri=base_url)
        #print(entity,e_class,parent)
        if isinstance(entity,(URIRef,BNode)) and e_class:
            if e_class==OME.Detail:
                return
            # if the entity is a Identifier, only create it if it relates to entity previously created
            logging.debug('create entity: {} {}'.format(entity,e_class))
            logging.debug('last entity: {} {}'.format(last_entity,relation))
            graph.add((entity, RDF.type, e_class))
            if isinstance(last_entity,(URIRef,BNode)) and relation:
                #print('create relation: {} {} {}'.format(last_entity,relation,entity))
                graph.add((last_entity, relation, entity))    
            else:
                logging.debug('missing relation: {} {} {} {}'.format(last_entity,e_class,relation,entity))
            for key, value in data.items():
                if key in ["@type", "@id"]:
                    #alrady handled
                    continue
                relation = get_entity_type(key)
                # if relation:
                #     logging.debug("key: {}".format(key),"relation: {}".format(relation))
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
                    logging.debug('a list at {} calling iterate_json with: {} {}'.format(key,entity,relation) )
                    # recursively inter over all json objects
                    iterate_json(value, graph, last_entity=entity, relation=relation)
                    # see if an entity is created and relate it if necessary
                else:
                    # if its no dict or list test if its kind of object/data/annotation property and set it
                    if (value or isinstance(value,bool)) and relation:
                        #graph.add((entity, relation, Literal(value)))
                        val_type=get_value_type(value)
                        if relation==QUDT.unit and value=="PIXEL":
                            graph.add((entity,relation,URIRef("http://qudt.org/vocab/unit/PT")))
                        else:
                            graph.add((entity,relation,Literal(value,datatype=val_type[1])))
                        if relation==QUDT.value:
                            graph.add((entity,RDF.type,QUDT.QuantityValue))
                        
                    elif not relation:
                        logging.debug('missing relation to Literal: {} {} {}'.format(entity,relation,value))
            
    elif isinstance(data, list):
        for item in data:
            logging.debug('start iter over list item' )            
            if  isinstance(base_url,(URIRef,BNode)):
                iterate_json(item, graph, last_entity=base_url, relation=OME.relates_to)
            else:
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




def create_instance_triple(data: dict, uri= None):
    entity=None
    o_class=None
    parent=None
    logging.debug( data.keys())
    if all(prop in data.keys() for prop in ['@type']):
        o_class = get_entity_type(data['@type'])
        print(data['@type'],o_class)
        #logging.debug(data['@type'],o_class)
        if o_class:
            #entity=URIRef(instance_id, TEMP)
            if isinstance(uri,URIRef):
                entity=uri
            else:
                entity=BNode()
        # if data['@type']=='as.dto.sample.SampleType':
        #     parent=OBIS.Object
        # elif data['@type']=='as.dto.experiment.ExperimentType':
        #     parent=OBIS.Collection
    return entity, o_class, parent
