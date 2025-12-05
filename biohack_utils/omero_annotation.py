import json

from omero.rtypes import rstring
from omero.model import MapAnnotationI, NamedValue


NS_COLLECTION = "ome/collection"
NS_NODE = "ome/collection/nodes"


def _build_image_url(image_id):
    """Return a relative OMERO.web URL for this image."""
    return f"https://omero-training.gerbi-gmb.de/webclient/img_detail/{image_id}/"


def _append_link_to_node_annotation(conn, image_id, link):
    """Append `link` to the 'attributes.link' field of the first NS_NODE
    map annotation of the given image.
    """
    img = conn.getObject("Image", image_id)
    if img is None:
        raise ValueError(f"Image {image_id} not found")

    anns = list(img.listAnnotations(ns=NS_NODE))
    if not anns:
        raise RuntimeError(
            f"No node annotation (ns={NS_NODE}) found for Image {image_id}"
        )

    node_ann = anns[0]  # you seem to expect exactly one node per image

    # Current key–value dict for this annotation
    kv = _map_ann_to_dict(node_ann)

    # Read existing links from "attributes.link" (JSON list or simple string)
    raw_links = kv.get("attributes.link")
    if raw_links is None:
        links = []
    else:
        links = json.loads(raw_links)
        if not isinstance(links, list):
            links = [str(links)]

    # Append if not already present
    if link not in links:
        links.append(link)

    # Store back as JSON string
    kv["attributes.link"] = json.dumps(links)

    # Convert back to list of NamedValue
    kv_pairs = [NamedValue(str(k), str(v)) for k, v in kv.items()]

    # Get the underlying IObject to update
    qs = conn.getQueryService()
    iann = qs.get("MapAnnotation", node_ann.getId())

    iann.setMapValue(kv_pairs)

    update_service = conn.getUpdateService()
    update_service.saveObject(iann)


def _map_ann_to_dict(ann):
    return {k: v for k, v in ann.getValue()}


def _create_collection(conn, name, version="0.x"):
    """Create a collection annotation (not linked to any image yet).
    Returns the annotation ID.
    """
    map_annotation = MapAnnotationI()
    map_annotation.setNs(rstring(NS_COLLECTION))

    kv_pairs = [
        NamedValue("version", version),
        NamedValue("type", "collection"),
        NamedValue("name", name)
    ]
    map_annotation.setMapValue(kv_pairs)

    # We save this in a server.
    update_service = conn.getUpdateService()
    saved = update_service.saveAndReturnObject(map_annotation)

    return saved.getId().getValue()


def _link_collection_to_image(conn, collection_ann_id, image_id):
    """Link an existing collection annotation to an image.
    """
    image = conn.getObject("Image", image_id)
    annotation = conn.getObject("MapAnnotation", collection_ann_id)

    if image is None:
        raise ValueError("Image {} not found".format(image_id))
    if annotation is None:
        raise ValueError("Annotation {} not found".format(collection_ann_id))

    image.linkAnnotation(annotation)


def _create_map_annotation(conn, kv, namespace):
    """Create a MapAnnotation with given key-value dict and namespace,
    save it and return the underlying I-object.
    """
    ann = MapAnnotationI()
    ann.setNs(rstring(namespace))

    kv_pairs = [NamedValue(str(k), str(v)) for k, v in kv.items()]
    ann.setMapValue(kv_pairs)

    update_service = conn.getUpdateService()
    saved = update_service.saveAndReturnObject(ann)
    return conn.getObject("MapAnnotation", saved.getId().getValue())


def _add_node_annotation(
    conn, image_id, node_type, collection_ann_id, node_name=None, attributes=None
):
    """Add a node annotation to an image describing its role in the collection.
    Returns the created annotation id.
    """
    kv = {
        "category": node_type,
        "collection_id": str(collection_ann_id),
    }
    if node_name:
        kv["name"] = node_name
    if attributes:
        for key, value in attributes.items():
            kv[key] = str(value)

    image = conn.getObject("Image", image_id)
    if image is None:
        raise ValueError(f"Image {image_id} not found")

    ann = _create_map_annotation(conn, kv, NS_NODE)
    image.linkAnnotation(ann)
    return ann.getId()


def _get_collection_members(conn, collection_ann_id):
    """Get all images linked to a collection annotation.
    """
    images = conn.getObjectsByAnnotations("Image", [collection_ann_id])
    return [img.getId() for img in images]


def _get_node_info(conn, image_id):
    """Get the node annotation (first one) for an image.
    Returns a dict or None.
    """
    img = conn.getObject("Image", image_id)
    if img is None:
        return None

    anns = list(img.listAnnotations(ns=NS_NODE))
    for ann in anns:
        return _map_ann_to_dict(ann)
    return None


def _get_collections(conn, image_id):
    """Get all collections an image is part of.
    Returns a list of dicts of how collections metadata should look like.
    """
    img = conn.getObject("Image", image_id)
    if img is None:
        return []

    coll_anns = list(img.listAnnotations(ns=NS_COLLECTION))

    collections = []
    for coll_ann in coll_anns:
        coll_ann_id = coll_ann.getId()
        coll_info = _map_ann_to_dict(coll_ann)

        member_ids = _get_collection_members(conn, coll_ann_id)
        members = []
        for member_id in member_ids:
            node_info = _get_node_info(conn, member_id)
            members.append({
                "image_id": member_id,
                "nodes": node_info,
            })

        collections.append({
            "collection_id": coll_ann_id,
            "name": coll_info.get("name"),
            "version": coll_info.get("version"),
            "members": members,
        })

    return collections


def _find_related_images(conn, image_id, node_type=None):
    """Given an image, find all related images in the same collection(s).
    Optionally filter by node_type (e.g., "label", "multiscale").

    Returns list of dicts
    """
    collections = _get_collections(conn, image_id)

    related = []
    for coll in collections:
        coll_id = coll["collection_id"]
        for member in coll["members"]:
            mid = member["image_id"]
            if mid == image_id:
                continue
            node_info = member["nodes"]
            if node_type is None or (node_info and node_info.get("type") == node_type):
                related.append({
                    "image_id": mid,
                    "collection_id": coll_id,
                    "nodes": node_info,
                })

    return related


def _find_images_with_collection_id_in_dataset(
    conn,
    collection_id,
    dataset_id,
    node_type=None,
    limit=None,
):
    """
    Find images in a given dataset that are members of a collection
    (identified by collection_id) and optionally have a given node_type.

    Returns a list of tuples:
        (image_id, image_name, collection_id)
    where collection_id is the collection annotation ID.
    """
    dataset = conn.getObject("Dataset", dataset_id)
    if dataset is None:
        print(f"Dataset {dataset_id} not found")
        return []

    collection_id = int(collection_id)

    # All members of this collection
    member_ids = set(_get_collection_members(conn, collection_id))

    # All images in the dataset
    dataset_images = list(dataset.listChildren())
    dataset_by_id = {img.getId(): img for img in dataset_images}

    images = []
    for mid in member_ids:
        if mid not in dataset_by_id:
            continue

        if limit is not None and len(images) >= limit:
            break

        img = dataset_by_id[mid]

        if node_type is not None:
            node_info = _get_node_info(conn, mid)
            if not node_info or node_info.get("type") != node_type:
                continue

        images.append((mid, img.getName(), collection_id))
        print(
            f"Match: Image ID={mid}, "
            f"Name='{img.getName()}', "
            f"Collection ID={collection_id}"
        )

    print(f"Found {len(images)} images with collection_id={collection_id} in dataset {dataset_id}")
    return images


def fetch_omero_labels_in_napari(conn, image_id, return_raw=False, label_node_type="Labels"):
    """Fetch label data for a given raw image using collections/nodes.

    Returns the raw and label array data.
    """
    raw_img = conn.getObject("Image", image_id)
    if raw_img is None:
        raise ValueError(f"Image {image_id} not found")

    collections = _get_collections(conn, image_id)
    if not collections:
        raise RuntimeError("Image is not part of any collection (namespace NS_COLLECTION).")

    labels_dict = {}
                # hack this to make it compatible with different naming of the kpv
    if label_node_type=='Labels':
        label_node_type='annotations'


    # Go through ALL collections this image is in
    for coll in collections:
        coll_id = coll["collection_id"]
        print(f"Processing collection {coll_id} (name={coll.get('name')})")

        for member in coll["members"]:
            mid = member["image_id"]
            node_info = member["nodes"] or {}

            # Skip the raw image itself
            if mid == image_id:
                continue

            
            # Filter by node type, e.g. "Labels"
            if label_node_type is not None and node_info.get("category") != label_node_type:
                continue

            img = conn.getObject("Image", mid)
            if img is None:
                continue

            # Use node "name" as key; fall back to image id
            node_name = node_info.get("name") or f"image_{mid}"
            print(f"Found label image: ID={mid}, node_name='{node_name}'")

            from napari_omero.plugins.loaders import get_data_lazy
            label_array = get_data_lazy(img)

            labels_dict[node_name] = label_array

    if not labels_dict:
        return labels_dict

    raw_data = get_data_lazy(raw_img)

    if return_raw:
        return raw_data, labels_dict
    else:
        return labels_dict
