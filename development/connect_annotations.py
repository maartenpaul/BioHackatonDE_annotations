from biohack_utils.util import omero_credential_parser, connect_to_omero
from biohack_utils import omero_annotation


def load_omero_labels_in_napari(conn, image_id):
    from biohack_utils.omero_annotation import fetch_omero_labels_in_napari

    raw_data, label_dict = fetch_omero_labels_in_napari(conn, image_id, return_raw=True)

    # Say hello to napari.
    import napari
    v = napari.Viewer()
    v.add_image(raw_data, blending="additive")
    for key, val in label_dict.items():
        v.add_labels(val, name=key)
    napari.run()


def write_annotations_to_image_and_labels(conn, image_id, label_id):
    # Creates a new collection based on label images.
    ann_id = omero_annotation._create_collection(conn, "cells", "0.0.1")

    # Links the collection to the raw image.
    omero_annotation._link_collection_to_image(conn, ann_id, image_id)

    # Add node annotations to the raw image
    omero_annotation._add_node_annotation(conn, image_id, "Intensities", ann_id, "Raw")

    # Links the collection to the label image.
    omero_annotation._link_collection_to_image(conn, ann_id, label_id)

    # Add node annotation to the label image.
    omero_annotation._add_node_annotation(conn, label_id, "Labels", ann_id, "Cell_Segmentation")


def main():
    parser = omero_credential_parser()
    args = parser.parse_args()

    conn = connect_to_omero(args)

    # Scripts to drop metadata.
    raw_id = 35394  # The available LIVECell image on the OMERO server.
    label_id = 35395  # The corresponding labels image for LIVECell on the OMERO server.

    # TODO: Check Martin's volume.
    # raw_id = 35494

    # Writes annotations in expected format.
    # write_annotations_to_image_and_labels(conn, raw_id, label_id)

    # Loading existing stuff.
    load_omero_labels_in_napari(conn, raw_id)

    conn.close()


if __name__ == "__main__":
    main()
