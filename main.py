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
import argparse
import json
#import omero.clients
from omero.gateway import BlitzGateway
from getpass import getpass

if __name__ == "__main__":
    #
    # Command line arguments that can be used
    #
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', help="The address of the OMERO server")
    parser.add_argument('--username', help="The username to log in to the OMERO server")
    parser.add_argument('--password', help="The password to log in to the OMERO server (INSECURE)")
    args = parser.parse_args()

    #
    # Connect to the OMERO server
    #
    while True:
        try:
            if args.server is None:
                server = input("Server: ")
            else:
                server = args.server

            if args.username is None:
                username = input("Username: ")
            else:
                username = args.username

            if args.password is None:
                password = getpass()
            else:
                password = args.password

            conn = BlitzGateway(username, password, host=server, port=4064, secure=True)

            if not conn.connect():
                raise Exception

            break
        except Exception:
            print("The connection to server", server, "failed. Please try again.")

    #
    # Get the list of all images the user has access to
    #
    all_images = conn.getObjects("Image")

    #
    # Loop through all images, get their original metadata and write
    # it to a file
    #
    for image in all_images:
        metadata = image.loadOriginalMetadata()
        f = open(image.getName()+".json", "w")
        f.write(json.dumps(metadata, indent=4))
        f.close()

    #
    # Disconnect from the OMERO server
    #
    conn.close()
