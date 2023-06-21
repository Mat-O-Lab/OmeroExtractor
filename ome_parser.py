from errno import ESTALE
from rdflib import BNode, URIRef, Literal, Graph, Namespace
from rdflib.util import guess_format
from rdflib.namespace import OWL, RDF 

from urllib.request import urlopen
from urllib.parse import urlparse, unquote
import configparser

OME_SOURCE = './ome.ttl'
OME_SOURCE_URL="https://github.com/Mat-O-Lab/OmeroExtractor/raw/main/ome.xml"
OME = Namespace(OME_SOURCE_URL+"#")

ome_original_meta=URIRef('original_meta')

ome_graph = Graph()
ome_graph.parse(OME_SOURCE, format='turtle')

def get_entity_type(string: str):
    hits = list(ome_graph[:OME.ome_type:Literal(string)])
    if hits:
        return hits[0]
    else:
        return None

class OMEtoRDF:
    """Class for Converting OME meta data json to RDF with help of OME Ontology.
    """
    def __init__(self,json_dict: dict={}, root_url: str='') -> None:
        #print(json_dict.keys())
        self.data=json_dict#.get('data',None)
        self.root=URIRef(root_url)
        #print(self.root_url)
        self.graph=Graph()
        #print(list(ome_graph[: RDF.type:]))
        
    def to_rdf(self):
        print('start mapping2\n\n\n\n\n\n')
        self.graph = Graph()
        #result.bind('data', _get_ns(base_url))
        iterate_json(self.data, self.graph, base_url=self.root)
        self.graph.bind('ome',OME)
        self.graph = fix_iris(self.graph, base_url=self.root)
        return self.graph


def iterate_json(data, graph, last_entity=None, relation=None, base_url=None):
    if isinstance(data, dict):
        # lookup if the id and type in dict result in a ontology entity
        entity, e_class, parent = create_instance_triple(data, base_url=base_url)
        #print(entity,e_class,parent)
        if entity and e_class:
            # if the entity is a Identifier, only create it if it relates to entity previously created
            #print('create entity: {} {}'.format(entity,e_class))
            #print('last entity: {} {}'.format(last_entity,relation))
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
                    #print('a dict at {} calling iterate_json with: {} {}'.format(key,entity,relation) )
                    # recursively inter over all json objects
                    iterate_json(value, graph, last_entity=entity, relation=relation, base_url=base_url)
                    # add the ObjectProperty to the created instance
                        
                elif isinstance(value, list):
                    #print('a list at {} calling iterate_json with: {} {}'.format(key,entity,relation) )
                    # recursively inter over all json objects
                    iterate_json(value, graph, last_entity=entity, relation=relation, base_url=base_url)
                    # see if an entity is created and relate it if necessary
                else:
                    # if its no dict or list test if its kind of object/data/annotation property and set it
                    if (value or isinstance(value,bool)) and relation:
                        graph.add((entity, relation, Literal(value)))
                    elif not relation:
                        print('missing relation to Literal: {} {} {}'.format(entity,relation,value))
            
    elif isinstance(data, list):
        for item in data:
            iterate_json(item, graph, last_entity=last_entity, relation=relation, base_url=base_url)


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

def create_instance_triple(data: dict, base_url=None):
    entity=None
    o_class=None
    parent=None
    #print( data.keys())
    if all(prop in data.keys() for prop in ['@type']):
        o_class = get_entity_type(data['@type'])
        if o_class:
            #entity=URIRef(instance_id, TEMP)
            entity=BNode()
        # if data['@type']=='as.dto.sample.SampleType':
        #     parent=OBIS.Object
        # elif data['@type']=='as.dto.experiment.ExperimentType':
        #     parent=OBIS.Collection
    return entity, o_class, parent
