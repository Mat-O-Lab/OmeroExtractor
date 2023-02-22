# OmeroExtractor
Tool to extract Meta Data from [OMERO.Server](https://www.openmicroscopy.org/omero/) by merging [OMERO.Web](https://github.com/ome/omero-web) JSON Api output with original meta data available and setting context.

# how to use

## create a .env file with
```bash
APP_PORT=<80>
ADMIN_MAIL=<email_of_admin>
```

## docker
Just pull the docker container from the github container registry
```bash
docker pull ghcr.io/mat-o-lab/omeroextractor:latest
```

## docker-compose
Clone the repo with 
```bash
git clone https://github.com/Mat-O-Lab/OmeroExtrator
```
cd into the cloned folder
```bash
cd OmeroExtrator
```
Build and start the container.
```bash
docker-compose up
```

A simple UI can be found at at the index page '/'
The API documentation at 'api/docs'