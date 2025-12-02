import numpy as np
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


def delete_annotations(conn, image_id):
    # ns = "ome/collection/"
    ns = "ome/collection/nodes"
    image = conn.getObject("Image", image_id)

    anns = list(image.listAnnotations(ns=ns))

    fanns = []
    for ann in anns:
        kv_dict = {k: v for k, v in ann.getValue()}
        print("Annotation ID:", ann.getId())
        print(kv_dict)
        fanns.append(ann.getId())

    conn.deleteObjects("Annotation", fanns, wait=True)


def _find_images_with_collection_id_in_dataset(conn, namespace, collection_id, dataset_id, limit=None):
    dataset = conn.getObject("Dataset", dataset_id)
    if dataset is None:
        print(f"Dataset {dataset_id} not found")
        return []

    collection_id = str(collection_id)
    images = []
    for i, img in enumerate(dataset.listChildren()):
        if limit is not None and i >= limit:
            break

        anns = list(img.listAnnotations(ns=namespace))
        for ann in anns:
            kv = {k: v for k, v in ann.getValue()}
            if kv.get("collection_id") == collection_id:
                images.append((img.getId(), img.getName(), ann.getId()))
                print(
                    f"Match: Image ID={img.getId()}, "
                    f"Name='{img.getName()}', "
                    f"Annotation ID={ann.getId()}"
                )
                # if you expect max one annotation per image, you can break here
                break

    print(f"Found {len(images)} images with collection_id={collection_id} in dataset {dataset_id}")
    return images


def _omero_image_to_2d_array(img, z=0, c=0, t=0):
    pixels = img.getPrimaryPixels()
    plane = pixels.getPlane(z, c, t)
    return np.asarray(plane)


def load_omero_labels_in_napari(conn, image_id):
    # NOTE: namespace seems like a random entity atm. Is there a convention behind it?
    ns = "ome/collection/nodes"
    raw_img = conn.getObject("Image", image_id)

    # HACK: assume exactly one collection annotation on the raw image
    anns = list(raw_img.listAnnotations(ns=ns))
    assert len(anns) == 1
    annotation_id = anns[0].getId()
    print("Raw image collection annotation_id:", annotation_id)

    # HACK: Search only within the same dataset
    dataset = raw_img.getParent()
    if dataset is None:
        raise RuntimeError("Image has no parent dataset; adjust search scope.")
    dataset_id = dataset.getId()
    print("Searching in dataset", dataset_id)

    matches = _find_images_with_collection_id_in_dataset(
        conn, namespace=ns, collection_id=annotation_id, dataset_id=dataset_id,
    )

    # Filter out the raw image; what remains should be label images
    label_candidates = [m for m in matches if m[0] != image_id]
    print("Label candidates:", label_candidates)
    if not label_candidates:
        raise RuntimeError("No label images found for this collection_id.")

    # For now, pick the first candidate
    label_img_id, label_name, _ = label_candidates[0]
    label_img = conn.getObject("Image", label_img_id)

    print(f"Using label image ID={label_img_id}, Name='{label_name}'")

    raw_data = _omero_image_to_2d_array(raw_img, z=0, c=0, t=0)
    label_data = _omero_image_to_2d_array(label_img, z=0, c=0, t=0)

    # Say hello to napari.
    import napari
    viewer = napari.Viewer()
    viewer.add_image(raw_data, name=raw_img.getName(), blending="additive")
    viewer.add_labels(label_data, name=label_name)

    napari.run()


def main():
    parser = omero_credential_parser()
    parser.add_argument("--delete", action="store_true")  # Deletes the existing metadata.
    args = parser.parse_args()

    conn = connect_to_omero(args)

    # upload_livecell(conn, args)

    # Scripts to drop metadata.
    raw_id = 35394  # The available LIVECell image on the OMERO server.
    label_id = 35395  # The corresponding labels image for LIVECell on the OMERO server.

    if args.delete:
        delete_annotations(conn, raw_id)
        delete_annotations(conn, label_id)

    collection_id = connect_annotations(conn, raw_id, args)
    connect_annotations(conn, label_id, args, collection_id=collection_id)

    # Read information for the current image id.
    read_information(conn, raw_id, args)
    read_information(conn, label_id, args)

    load_omero_labels_in_napari(conn, raw_id)

    conn.close()


if __name__ == "__main__":
    main()
