#
# This file is part of the Mat-O-Lab project (https://github.com/Mat-O-Lab/).
# Copyright (c) 2022 Alexander Reinholdt.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
import requests
import json
from getpass import getpass

#
# Get the server and the credentials
#
print("Please enter the server and the user's credentials.")
server = "195.90.200.163" # input("Server: ")
username = "alexander.reinholdt" # input("Username: ")
password = getpass("Password: ")

#
# Create a session
#
session = requests.Session()

#
# Get the supported APIs as well as the connected base URLs
#
r = session.get("http://" + server + "/api/").json()

#
# We want the latest API's base url for working with the images
#
# NOTE: '-1' is the latest api tuple in the returned json output. Read
# out the base url for further processing
#
base_url = r["data"][-1]["url:base"]

#
# Now get all URLs the server supports. We will pick the ones we need
# from the output.
#
all_urls = session.get(base_url).json()

#
# Get the token for login
#
token_url = all_urls["url:token"]
token = session.get(token_url).json()["data"]

#
# Get the login URL
#
login_url = all_urls["url:login"]

#
# List of servers
#
servers_url = all_urls["url:servers"]
servers = session.get(servers_url).json()["data"]

#
# FIXME: We assume that there is only one server for now.
#  So,blindly use the first entry.
#
server = servers[0]

#
# Credentials for the login
#
credentials = {"username": username,
               "password": password,
               "csrfmiddlewaretoken": token,
               "server": server["id"]}

#
# Log in to the server and check if we succeeded
#
return_value = session.post(login_url, data=credentials)
response = return_value.json()

assert return_value.status_code == 200
assert response["success"]

#
# Get the list of projects we have access to
#
projects_url = all_urls["url:projects"]
projects = session.get(projects_url).json()

#
# Now get all available images in the projects and write
# their metadata into files (one for each image)
#
for p in projects["data"]:
    # Get the URL for the datasets of the project
    project_url = projects_url + str(p["@id"]) + "/"
    project = session.get(project_url).json()
    project_datasets_url = project["data"]["url:datasets"]
    # Get the datasets from the respective project
    project_datasets = session.get(project_datasets_url).json()
    # Get the images from the datasets
    for d in project_datasets["data"]:
        project_images_url = d["url:images"]
        project_images = session.get(project_images_url).json()
        # Write the metadata of each image into a json file
        for i in project_images["data"]:
            image_url = i["url:image"]
            json_data = session.get(image_url).json()
            json_data.update({"ImageUrl": image_url})
            f = open(json_data["data"]["Name"]+".json", "w")
            f.write(json.dumps(json_data, indent=4, sort_keys=True))
            f.close()

print("All metadata saved. Goodbye.")
