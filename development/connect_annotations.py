from biohack_utils.util import omero_credential_parser, connect_to_omero
from biohack_utils import omero_annotation


def load_omero_labels_in_napari(conn, image_id, is_3d=False):
    if isinstance(image_id, list):  # If it's a list, only check one image.
        image_id = image_id[0]

    from biohack_utils.omero_annotation import fetch_omero_labels_in_napari

    raw_data, label_dict = fetch_omero_labels_in_napari(
        conn, image_id, return_raw=True, is_3d=is_3d, label_node_type="Labels"
    )

    if isinstance(image_id, list):
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
        if val.dtype == float:  # for image data.
            v.add_image(val, name=key)
        else:  # for label data.
            v.add_labels(val, name=key)
    napari.run()


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


def main():
    parser = omero_credential_parser()
    args = parser.parse_args()

    conn = connect_to_omero(args)

    # Scripts to drop metadata.

    # 1. For LIVECell (2d)
    # raw_id = 35394  # The available LIVECell image on the OMERO server.
    # label_id = 35395  # The corresponding labels image for LIVECell on the OMERO server.

    # 2. For CochleaNet (3d)
    # raw_id = 35499
    # label_id = 35500

    # 3. For multi-label images (2d)
    # raw_id = 35478

    # 4. For CovidIF HCS data (2d)
    raw_id = [35501, 35502]
    label_id = 35503

    # Writes annotations in expected format.
    # write_annotations_to_image_and_labels(conn, raw_id, label_id)

    # Loading existing stuff.
    load_omero_labels_in_napari(conn, raw_id, is_3d=False)

    conn.close()


if __name__ == "__main__":
    main()
