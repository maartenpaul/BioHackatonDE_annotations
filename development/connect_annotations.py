import imageio.v3 as imageio

from omero.gateway import MapAnnotationWrapper

from omero_utils import omero_credential_parser, connect_to_omero


def upload_livecell(conn, args):
    dataset = conn.getObject("Dataset", args.dataset_id)

    # file_path = "/home/anwai/.cache/micro_sam/sample_data/livecell-2d-image.png"
    file_path = "/home/anwai/data/livecell_segmentation.png"

    images = [imageio.imread(file_path)]
    image = conn.createImageFromNumpySeq(
        (im for im in images),
        dataset=dataset,
        imageName="LiveCell Labels",
        description="Segmentation of cells imaged in phase-contrast microscopy",
    )

    print(f"Created image with ID: {image.id}")


def connect_annotations(conn, image_id, args, collection_id=None):
    namespace = "ome/collection/"

    d = {
        "collection_name": "livecell",
        "collection_type": "dummy_collection",
    }
    if collection_id:
        d["collection_id"] = f"{collection_id}"

    image = conn.getObject("Image", image_id)

    # Create the MapAnnotation
    map_ann = MapAnnotationWrapper(conn)
    map_ann.setNs(namespace)

    # setValue expects a list of (name, value) pairs
    map_ann.setValue(list(d.items()))

    # Save the annotation object
    map_ann.save()

    # Link the annotation to the image
    image.linkAnnotation(map_ann)

    if collection_id is None:
        annotation_id = map_ann.getId()
        print("Created MapAnnotation with ID:", annotation_id)
        return annotation_id


def read_information(conn, image_id, args):
    ns = "ome/collection/"
    image = conn.getObject("Image", image_id)

    anns = list(image.listAnnotations(ns=ns))

    for ann in anns:
        kv_dict = {k: v for k, v in ann.getValue()}
        print("Annotation ID:", ann.getId())
        print(kv_dict)


def main():
    parser = omero_credential_parser()
    args = parser.parse_args()

    conn = connect_to_omero(args)

    upload_livecell(conn, args)

    # Scripts to drop metadata.
    raw_id = 35394  # The available LIVECell image on the OMERO server.
    label_id = 35395  # The corresponding labels image for LIVECell on the OMERO server.
    collection_id = connect_annotations(conn, raw_id, args)
    connect_annotations(conn, label_id, args, collection_id=collection_id)

    # Read information for the current image id.
    read_information(conn, raw_id, args)
    read_information(conn, label_id, args)

    conn.close()


if __name__ == "__main__":
    main()
