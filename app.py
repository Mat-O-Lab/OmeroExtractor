# app.py

import os

import uvicorn
from starlette_wtf import StarletteForm
from starlette.responses import HTMLResponse
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Any

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
    version: str = "v0.0.1"
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
    
@app.get("/", response_class=HTMLResponse)
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

@app.post("/api")
async def api(apirequest: ApiRequest) -> dict:
    try:
        result = {"test": apirequest.image_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return result


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