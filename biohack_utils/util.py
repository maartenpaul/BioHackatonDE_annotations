import argparse
import numpy as np

from omero.gateway import BlitzGateway


def _upload_image(conn, curr, iname):
    images = [curr]
    image = conn.createImageFromNumpySeq(
        (im for im in images),
        imageName=iname,
    )
    return image.id


def _upload_volume(conn, curr, iname):
    # Upload the image and corresponding labels
    image = conn.createImageFromNumpySeq(
        (plane for plane in curr),
        sizeZ=curr.shape[0],
        sizeC=1,
        sizeT=1,
        imageName=iname,
    )
    return image.id


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


def fetch_omero_labels_in_napari(conn, image_id, return_raw=False):
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

    if return_raw:
        return raw_data, label_data
    else:
        return label_data


def connect_to_omero(args):
    USERNAME = args.username
    PASSWORD = args.password
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
    parser.add_argument("-u", "--username", type=str, required=True)
    parser.add_argument("-p", "--password", type=str, required=True)
    parser.add_argument("--image_id", type=int)
    parser.add_argument("--namespace", type=str, default="ome/collection")
    return parser
