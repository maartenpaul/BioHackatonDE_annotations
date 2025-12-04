import argparse
import json
from typing import List, Optional

import numpy as np

from biohack_utils.util import connect_to_omero, _upload_image, _upload_volume
from biohack_utils import omero_annotation
from biohack_utils.omero_annotation import NS_NODE


DEFAULT_COLLECTION = {
    "version": "0.0.1",
    "type": "collection",
    "name": "cells",
}


def load_omero_labels_in_napari(conn, image_id, is_3d=False):
    id_was_a_list = isinstance(image_id, list)
    if isinstance(image_id, list):  # If it's a list, only check one image.
        image_id = image_id[0]

    from biohack_utils.omero_annotation import fetch_omero_labels_in_napari

    raw_data, label_dict = fetch_omero_labels_in_napari(
        conn, image_id, return_raw=True, is_3d=is_3d, label_node_type="Labels"
    )

    if id_was_a_list:
        # Well the assumption is there are multiple images. So, gotta catch them all.
        ldict = fetch_omero_labels_in_napari(
            conn, image_id, return_raw=False, is_3d=is_3d, label_node_type="Intensities"
        )
        label_dict = {**label_dict, **ldict}

    # Say hello to napari.
    import napari
    v = napari.Viewer()
    v.add_image(raw_data, blending="additive")
    for key, val in label_dict.items():
        v.add_image(val, name=key)
    napari.run()


def get_collection_dict(json_dict, target_key="type", target_value="collection"):
    for (key, value) in json_dict.items():
        if isinstance(value, dict):
            if target_key in list(value.keys()):
                if value[target_key] == target_value:
                    return value
    return None


def write_annotation_to_image(
    conn,
    json_dict: str,
    image_ids: Optional[List[int]] = None,
    image_arr: Optional[np.ndarray] = None,
    collection_id: Optional[int] = None,
):
    if image_ids is None:
        image_ids = [int(key) for key in json_dict[NS_NODE]]

    print(image_ids)
    if image_ids is None and image_arr is None:
        raise ValueError("Supply either image ID or an array.")

    if image_arr is not None:
        # TODO get correct entry of name
        name = json_dict["name"]

        if len(image_arr.shape) == 2:
            image_id = _upload_image(conn, image_arr, name)

        elif len(image_arr.shape) == 3:
            image_id = _upload_volume(conn, image_arr, name)

        else:
            raise ValueError("Input data must have 2D or 3D shape.")
        image_ids = [image_id]

    # create new collection if collection_id is not supplied
    if collection_id is None:
        collection_dict = get_collection_dict(json_dict)
        if collection_dict is None:
            collection_dict = DEFAULT_COLLECTION

        collection_id = omero_annotation._create_collection_from_dict(conn, collection_dict)

    for image_id in image_ids:
        print("Link collection to an image")
        omero_annotation._link_collection_to_image(conn, collection_id, image_id)

        node_dict = json_dict[NS_NODE][str(image_id)]

        omero_annotation._add_node_annotation_from_dict(conn, image_id, collection_id, node_dict)

    for iid in image_ids:
        print("Build image url")
        link = omero_annotation._build_image_url(iid)
        omero_annotation._append_link_to_node_annotation(conn, iid, link)


def write_annotations_to_image_and_labels(conn, image_id, label_id):
    # Creates a new collection based on label images.
    ann_id = omero_annotation._create_collection(conn, "cells", "0.0.1")

    if isinstance(image_id, int):
        image_id = [image_id]

    for curr_iid in image_id:  # Links multiple image ids.
        # Links the collection to the raw image.
        omero_annotation._link_collection_to_image(conn, ann_id, curr_iid)
        # Add node annotations to the raw image
        omero_annotation._add_node_annotation(conn, curr_iid, "Intensities", ann_id, "Raw")

    # Links the collection to the label image.
    omero_annotation._link_collection_to_image(conn, ann_id, label_id)
    # Add node annotation to the label image.
    omero_annotation._add_node_annotation(conn, label_id, "Labels", ann_id, "Cell_Segmentation")

    # Finally, let's build a pseudo-network by linking all links.
    all_image_ids = image_id + [label_id]
    for iid in all_image_ids:
        link = omero_annotation._build_image_url(iid)
        omero_annotation._append_link_to_node_annotation(conn, iid, link)


def main():
    parser = argparse.ArgumentParser(
        description="Connect ids.")

    parser.add_argument("-u", "--username", type=str, required=True)
    parser.add_argument("-p", "--password", type=str, required=True)

    parser.add_argument("--raw_id", nargs="+", type=int, default=None)
    parser.add_argument("--label_id", type=int, default=None)

    parser.add_argument("--json", type=str, default=None,
                        help="Path to dictionary in JSON format.")
    parser.add_argument("--collection_id", type=str, default=None,
                        help="Collection ID to add images to. Per default, a new collection will be created.")

    args = parser.parse_args()

    conn = connect_to_omero(args)

    # Scripts to drop metadata.
    if args.raw_id is not None and args.label_id is not None:

        # 1. For LIVECell (2d)
        # raw_id = 35394  # The available LIVECell image on the OMERO server.
        # label_id = 35395  # The corresponding labels image for LIVECell on the OMERO server.

        # 2. For CochleaNet (3d)
        # raw_id = 35499
        # label_id = 35500

        # 3. For multi-label images (2d)
        # raw_id = 35478

        # 4. For CovidIF HCS data (2d)
        # raw_id = [35501, 35502]
        # label_id = 35503

        # Writes annotations in expected format.
        write_annotations_to_image_and_labels(conn, args.raw_id, args.label_id)

    elif args.json is not None:
        with open(args.json) as f:
            json_dict = json.load(f)
        write_annotation_to_image(conn, json_dict, collection_id=args.collection_id)
    else:
        conn.close()
        raise ValueError("Supply either raw or label id or a JSON dictionary.")

    conn.close()


if __name__ == "__main__":
    main()
