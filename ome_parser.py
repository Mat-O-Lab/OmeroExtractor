from errno import ESTALE
from rdflib import BNode, URIRef, Literal, Graph, Namespace
from rdflib.util import guess_format
from rdflib.namespace import OWL, RDF 

from urllib.request import urlopen
from urllib.parse import urlparse, unquote

OME_SOURCE = './ome.ttl'
OME_SOURCE_URL="https://github.com/Mat-O-Lab/OmeroExtractor/raw/main/ome.xml#"
OME = Namespace(OME_SOURCE_URL)
OME_XSD_URL='http://www.openmicroscopy.org/Schemas/OME/2016-06#'


ome_graph = Graph()
ome_graph.parse(OME_SOURCE, format='turtle')


def map_object(object: dict,graph: Graph, root: URIRef):
    entry=BNode()
    type=''        
    for k, v in object.items():
        short_iri=k.rsplit('#',1)[-1].rsplit(':',1)[-1]
        lookup=URIRef(OME_SOURCE_URL+short_iri)

        hit=next(ome_graph[lookup:],'')
        print('root: {} key: {} value: {} lookup: {}'.format(root,k,v,lookup))
        print(hit)
        if isinstance(v, dict):
            #print('is dict -> recursiv')
            if hit:
                target=BNode()
                print('creating: {} {} {}'.format(entry,hit[0],target))
                graph.add((entry,lookup,target))
                map_object(v,graph,target)
            else:
                map_object(v,graph,root)
        else:
            if short_iri=='@id':
                entry_with_id=URIRef(str(v))
                for po in graph[entry::]:
                    print('creating: {} {} {}'.format(entry_with_id,po[0],po[1]))
                    graph.add((entry_with_id,po[0],po[1]))
                    graph.remove((entry,None, None))
                entry=entry_with_id
            elif short_iri=='@type':
                type=URIRef(v)
            elif hit:
                value=Literal(v)
                print('creating: {} {} {}'.format(entry,hit[1],value))
                graph.add((entry,lookup,value))
            elif k=='Value':
                value=Literal(v)
                print('creating: {} {} {}'.format(entry,RDF.value,value))
                graph.add((entry,RDF.value,value))
            else:
                #add also not found entities - additional ontology work is needed
                value=Literal(v)
                print('entity {} not found, adding as property'.format(lookup))
                print('creating: {} {} {}'.format(entry,lookup,value))
                graph.add((entry,lookup,value))

        if type:
            graph.add((entry,RDF.type,type))
            #remove Bnode and reconnect new one
            for sp in graph[::root]:
                graph.add((sp[0],sp[1],entry))
                graph.remove((None,None, root))
        # if k=="omero:details":
        #     break
                
            # if (entry, RDF.type, OWL.Class) in ome_graph:
            #     print("Ome Ontology Class entity for {} found.".format(short_iri))
            # elif (entry, RDF.type, OWL.ObjectProperty) in ome_graph:
            #     print("Ome Ontology object property entity for {} found.".format(short_iri))
            # else:
            #     print("Ome Ontology entity for {} not found.".format(short_iri))#
    return graph

class OMEtoRDF:
    """Class for Converting OME meta data json to RDF with help of OME Ontology.
    """
    def __init__(self,json_dict: dict={}, root_url: str='') -> None:
        #print(json_dict.keys())
        self.data=json_dict#.get('data',None)
        self.original_meta=json_dict.get('original_meta',None)
        self.root=URIRef(root_url)
        #print(self.root_url)
        self.graph=Graph()
        self.graph.bind('ome',OME_SOURCE_URL)
        #print(list(ome_graph[: RDF.type:]))
        
    def to_rdf(self):
        print('start mapping\n\n\n\n\n\n')
        target=BNode()
        self.graph.add((self.root,OME.Image,target))
        self.graph=map_object(self.data,self.graph,target)
        return self.graph
