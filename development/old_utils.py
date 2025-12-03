import imageio.v3 as imageio

from omero.gateway import MapAnnotationWrapper


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
    namespace = "ome/collection/nodes"

    d = {
        "version": "0.0.1",
        "collection_name": "livecell",
        "collection_type": "dummy_collection",
    }

    if collection_id:  # i.e. it is a label image.
        d["collection_id"] = f"{collection_id}"
        d["image_type"] = "labels"
        d["attributes"] = {"class_labels": "cells"}
    else:  # Otherwise the raw image.
        d["image_type"] = "raw"
        d["type"] = "intensity"

    image = conn.getObject("Image", image_id)

    # Create the MapAnnotation
    map_ann = MapAnnotationWrapper(conn)
    map_ann.setNs(namespace)

    # setValue expects a list of (name, value) pairs
    kv_list = [(k, str(v)) for k, v in d.items()]
    map_ann.setValue(kv_list)

    # Save the annotation object
    map_ann.save()

    # Link the annotation to the image
    image.linkAnnotation(map_ann)

    annotation_id = map_ann.getId()
    if collection_id is None:  # i.e. still the raw image.
        # Here, we finalize the collection id.  Let's go ahead with adding it to the raw image too.
        d["collection_id"] = f"{annotation_id}"
        kv_list = [(k, str(v)) for k, v in d.items()]
        map_ann.setValue(kv_list)
        map_ann.save()

        print("Created MapAnnotation with ID:", annotation_id)
        return annotation_id


def read_information(conn, image_id, args):
    ns = "ome/collection/nodes"
    image = conn.getObject("Image", image_id)

    anns = list(image.listAnnotations(ns=ns))

    for ann in anns:
        kv_dict = {k: v for k, v in ann.getValue()}
        print("Annotation ID:", ann.getId())
        print(kv_dict)
