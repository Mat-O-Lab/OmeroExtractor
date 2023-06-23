# app.py

import os

import uvicorn
import requests
from requests.compat import urljoin, urlparse
from starlette_wtf import StarletteForm
from starlette.responses import HTMLResponse
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Any
import json

from pydantic import BaseSettings, BaseModel, Field

from fastapi import Request, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from wtforms import SelectField, BooleanField, IntegerField

import logging
import configparser
from enum import Enum
from settings import Settings

settings = Settings()

class ReturnType(str, Enum):
    jsonld="json-ld"
    n3="n3"
    nquads="nquads"
    nt="nt"
    hext="hext"
    prettyxml="pretty-xml"
    trig="trig"
    trix="trix"
    turtle="turtle"
    longturtle="longturtle"
    xml="xml"

middleware = [Middleware(SessionMiddleware, secret_key='super-secret')]
app = FastAPI(
    title=settings.app_name,
    description=settings.description,
    version=settings.version,
    contact=settings.contact,
    license_info=settings.license,
    openapi_url=settings.openapi_url,
    docs_url=settings.docs_url,
    redoc_url=None,
    swagger_ui_parameters= {'syntaxHighlight': False},
    middleware=middleware
)
app.add_middleware(
CORSMiddleware,
allow_origins=["*"], # Allows all origins
allow_credentials=True,
allow_methods=["*"], # Allows all methods
allow_headers=["*"], # Allows all headers
)
app.add_middleware(uvicorn.middleware.proxy_headers.ProxyHeadersMiddleware, trusted_hosts="*")

app.mount("/static/", StaticFiles(directory='static', html=True), name="static")
templates= Jinja2Templates(directory="templates")

logging.basicConfig(level=logging.WARNING)

templates.env.globals['APP_NAME'] = "OmeroExtractor"
templates.env.globals['APP_DESCRIPTION'] = 'Tool to extract Meta Data from <a href="https://www.openmicroscopy.org/omero/">OMERO.server</a> by merging <a href="https://github.com/ome/omero-web">OMERO.web</a> JSON Api output with original meta data available and setting context.'

import ome_parser

  
class StartForm(StarletteForm):
    image_id = IntegerField(
        'Image Id',
        #validators=[DataRequired()],
        description='Id of Omero server Image',
        render_kw={"placeholder": 1},
    )
    
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request):
    """GET /: form handler
    """
    start_form = await StartForm.from_formdata(request)
    result = ''
    return templates.TemplateResponse("index.html",
        {"request": request,
        "start_form": start_form,
        "result": result
        }
    )

class OmeroWebSession(requests.Session):
    def __init__(self, host=None):
        super().__init__()
        self.host=host
        self.base_url=''
        start_url='{}/api/'.format(self.host)
        print(start_url)
        try:
            get_api_url=self.get(start_url)
            self.base_url = get_api_url.json()["data"][-1]["url:base"]
            self.urls=self.get(self.base_url).json()
            self.urls['url:original_meta']='{}/webclient/download_orig_metadata/'.format(host)
        except Exception as e:
            logging.error('could not init Omero Web Api Session: {}'.format(str(e)))
    def login(self,username,password):
        token_url = self.urls["url:token"]
        logging.info("getting session crsf token at {}".format(token_url))
        token = self.get(token_url).json()["data"]
        login_url = self.urls["url:login"]
        credentials = {
                "username": username,
                "password": password,
                "csrfmiddlewaretoken": token,
                "server": 1
                }
        #login and test connection
        logging.info("trying to login at {} with given credentials".format(login_url))
        return_value = self.post(url=login_url,data=credentials)
        if return_value.status_code == 200:
            logging.info('login successful: {}'.format(return_value.json()))
            return True
        else:
            logging.error('login failed: {}'.format(return_value))
            return False
    def get_image_meta(self, id: int):
        self.urls["url:images"]
        request_url=self.urls["url:images"]+'{}'.format(str(id))
        return_value = self.get(request_url)
        if return_value.status_code == 200:
            return request_url, return_value.json()
        else:
            logging.error('Could not get meta data from omero web json api: {}'.format(return_value))
            raise HTTPException(status_code=500, detail='Could not get meta data from omero web json api: {}'.format(return_value))
    
    def get_dataset_meta(self, id: int):
        self.urls["url:datasets"]
        request_url=self.urls["url:datasets"]+'{}'.format(str(id))
        return_value = self.get(request_url)
        if return_value.status_code == 200:
            return request_url, return_value.json()
        else:
            logging.error('Could not get meta data from omero web json api: {}'.format(return_value))
            raise HTTPException(status_code=500, detail='Could not get meta data from omero web json api: {}'.format(return_value))

    def get_rois_meta(self, id: int):
        self.urls["url:images"]
        request_url=self.urls["url:images"]+'{}'.format(str(id))+"/rois/"
        return_value = self.get(request_url)
        if return_value.status_code == 200:
            return request_url, return_value.json()
        else:
            logging.error('Could not get meta data from omero web json api: {}'.format(return_value))
            raise HTTPException(status_code=500, detail='Could not get meta data from omero web json api: {}'.format(return_value))

    def get_original_image_meta(self, id: int):
        self.urls['url:original_meta']
        return_value = self.get(self.urls['url:original_meta']+'{}'.format(str(id)))
        if return_value.status_code == 200:
            cfg_parser=configparser.ConfigParser(strict=False)
            try:
                cfg_parser.read_string(return_value.text)
            except:
                pass
            result={**cfg_parser._sections,**{'@type': 'OriginalMeta'}}
            return result
        else:
            logging.error('Could not get original meta data from omero web client: {}'.format(return_value))
            raise HTTPException(status_code=500, detail='Could not get original meta data from omero web client: {}'.format(return_value))

    def request(self, method, url, *args, **kwargs):
        #test if relativc url
        if not urlparse(url).netloc:
            logging.error('got relativ url joining: {} with {}'.format(self.host,url))
            joined_url=urljoin(self.host,url)
        else:
            joined_url=url
        return super().request(method, joined_url, *args, **kwargs)

def open_api_session(host,username: str=os.getenv('OMERO_WEB_USER', default='root'), password: str=os.getenv('OMERO_WEB_PASS', default=os.getenv('OMERO_ROOT_PASS', default=''))):
    session = OmeroWebSession(host)
    if session.login(username, password):
        return session
    else:
        return None
    
@app.get("/api/image/{id}")
async def get_image_meta(request: Request, id: int, anonymize: bool = True, format: ReturnType=ReturnType.jsonld):
    host=os.getenv('OMERO_WEB_HOST',default='http://omeroweb:4080')
    session = open_api_session(host)
    if not session:
        return {}
    url, meta = session.get_image_meta(id)
    meta=meta['data']
    original_meta = session.get_original_image_meta(id)
    #add original_meta to json
    #print(original_meta)
    meta['original_meta']=original_meta
                
    # Serializing json
    json_object = json.dumps(meta, indent=4)
    
    #Writing to sample.json
    with open("tests/image{}.json".format(id), "w") as outfile:
        outfile.write(json_object)

    converter=ome_parser.OMEtoRDF(meta, root_url=url)
    converter.annotate_prov(str(request.url),settings)
    result=converter.to_rdf(anonymize=anonymize)
    data=result.serialize(format=format.value,auto_compact=True,indent=4)
    if format==ReturnType.jsonld:
        return json.loads(data)
    else:
        return data

@app.get("/api/dataset/{id}")
async def get_dataset_meta(request: Request, id: int, anonymize: bool = True, format: ReturnType=ReturnType.jsonld):
    host=os.getenv('OMERO_WEB_HOST',default='http://omeroweb:4080')
    session = open_api_session(host)
    if not session:
        return {}
    url, meta = session.get_dataset_meta(id)
    meta=meta['data']
       # Serializing json
    json_object = json.dumps(meta, indent=4)
    
    #Writing to sample.json
    with open("tests/dataset{}.json".format(id), "w") as outfile:
        outfile.write(json_object)

                
    converter=ome_parser.OMEtoRDF(meta, root_url=url)
    converter.annotate_prov(str(request.url),settings)
    result=converter.to_rdf(anonymize=anonymize)
    data=result.serialize(format=format.value,auto_compact=True,indent=4)
    if format==ReturnType.jsonld:
        return json.loads(data)
    else:
        return data


@app.get("/api/rois/{id}")
async def get_rois_meta(request: Request, id: int, anonymize: bool = True, format: ReturnType=ReturnType.jsonld):
    host=os.getenv('OMERO_WEB_HOST',default='http://omeroweb:4080')
    session = open_api_session(host)
    if not session:
        return {}
    url, meta = session.get_rois_meta(id)
    meta=meta['data']
       # Serializing json
    json_object = json.dumps(meta, indent=4)
    
    #Writing to sample.json
    with open("tests/rois{}.json".format(id), "w") as outfile:
        outfile.write(json_object)

                
    converter=ome_parser.OMEtoRDF(meta, root_url=url)
    converter.annotate_prov(str(request.url),settings)
    result=converter.to_rdf(anonymize=anonymize)
    data=result.serialize(format=format.value,auto_compact=True,indent=4)
    if format==ReturnType.jsonld:
        return json.loads(data)
    else:
        return data

@app.get("/api/info", response_model=Settings)
async def info() -> dict:
    return settings

#time http calls
from time import time
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time()
    response = await call_next(request)
    process_time = time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app_mode=os.environ.get("APP_MODE") or 'production'
    if app_mode=='development':
        reload=True
        access_log=True
    else:
        reload=False
        access_log=False
    uvicorn.run("app:app",host="0.0.0.0",port=port, reload=reload, access_log=access_log)