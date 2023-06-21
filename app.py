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

class Settings(BaseSettings):
    app_name: str = "OmeroExtractor"
    admin_email: str = os.environ.get("ADMIN_MAIL") or "omeroextractor@matolab.org"
    items_per_user: int = 50
    version: str = "v0.0.2"
    config_name: str = os.environ.get("APP_MODE") or "development"
    openapi_url: str ="/api/openapi.json"
    docs_url: str = "/api/docs"
settings = Settings()


middleware = [Middleware(SessionMiddleware, secret_key='super-secret')]
app = FastAPI(
    title="OmeroExtractor",
    description="Tool to extract Meta Data from Omero Server and provide as json-ld.",
    version=settings.version,
    contact={"name": "Thomas Hanke, Mat-O-Lab", "url": "https://github.com/Mat-O-Lab", "email": settings.admin_email},
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
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

logging.basicConfig(level=logging.DEBUG)

templates.env.globals['APP_NAME'] = "OmeroExtractor"
templates.env.globals['APP_DESCRIPTION'] = 'Tool to extract Meta Data from <a href="https://www.openmicroscopy.org/omero/">OMERO.server</a> by merging <a href="https://github.com/ome/omero-web">OMERO.web</a> JSON Api output with original meta data available and setting context.'

import ome_parser

class ApiRequest(BaseModel):
    image_id: int = Field(1, title='Image ID', description='Id of a Omero Image')
    class Config:
        schema_extra = {
            "example": {
                "image_id": 1
            }
        }

    
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
            self.urls['ur:original_meta']='{}/webclient/download_orig_metadata/'.format(host)
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
    def get_original_image_meta(self, id: int):
        self.urls['ur:original_meta']
        return_value = self.get(self.urls['ur:original_meta']+'{}'.format(str(id)))
        if return_value.status_code == 200:
            return return_value.text
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

@app.post("/api/imagemeta")
async def imagemeta(apirequest: ApiRequest) -> dict:
    host=os.getenv('OMERO_WEB_HOST',default='http://omeroweb:4080')
    session = open_api_session(host)
    if not session:
        return {}
    url, image_meta = session.get_image_meta(apirequest.image_id)
    image_meta=image_meta['data']
    original_meta = session.get_original_image_meta(apirequest.image_id)
    #add original_meta to json
    #print(original_meta)
    image_meta['original_meta']=original_meta
    # Serializing json
    json_object = json.dumps(image_meta, indent=4)
    
    # Writing to sample.json
    with open("tests/sample.json", "w") as outfile:
        outfile.write(json_object)
    
    converter=ome_parser.OMEtoRDF(image_meta, url)
    result=converter.to_rdf()
    #result.serialize(format='turtle', destination='sample2.ttl',auto_compact=True,indent=4)
    return json.loads(result.serialize(format='json-ld',auto_compact=True,indent=4))
    

@app.get("/info", response_model=Settings)
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