import argparse

from omero.gateway import BlitzGateway


def connect_to_omero(args):
    USERNAME = args.username
    PASSWORD = args.password
    # HOST = "omero.tim2025.de"
    HOST = "omero-training.gerbi-gmb.de"
    PORT = 4064  # Default OMERO port

    conn = BlitzGateway(USERNAME, PASSWORD, host=HOST, port=PORT)
    conn.connect()

    if conn.isConnected():
        print("Connected to OMERO")
    else:
        print("Failed to connect")
        exit(1)

    return conn


def omero_credential_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", required=True)
    parser.add_argument("-p", "--password", required=True)
    # This is the ID of the omero test dataset.
    parser.add_argument("-d", "--dataset_id", default=25780, type=int)
    # This is the ID of the Lucchi data in omero.
    # parser.add_argument("--image_id", default=108133, type=int)
    # This is the ID of the Livecell data in omero.
    parser.add_argument("--image_id", default=108177, type=int)
    return parser
