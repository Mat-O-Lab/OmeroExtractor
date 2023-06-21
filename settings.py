import os
from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str = "OmeroExtractor"
    admin_email: str = os.environ.get("ADMIN_MAIL") or "omeroextractor@matolab.org"
    items_per_user: int = 50
    version: str = "v0.0.3"
    config_name: str = os.environ.get("APP_MODE") or "development"
    openapi_url: str ="/api/openapi.json"
    docs_url: str = "/api/docs"
    source: str = "https://github.com/Mat-O-Lab/OmeroExtractor"
    description: str = "Tool to extract Meta Data from Omero Server and provide as json-ld."
    contact: dict={"name": "Thomas Hanke, Mat-O-Lab", "url": "https://github.com/Mat-O-Lab", "email": os.environ.get("ADMIN_MAIL") or "omeroextractor@matolab.org"}
    license: dict={"name": "Apache 2.0","url": "https://www.apache.org/licenses/LICENSE-2.0.html"}
    
    

