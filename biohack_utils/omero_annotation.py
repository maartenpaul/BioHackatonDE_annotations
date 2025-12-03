import ezomero
from omero.model import MapAnnotationI, NamedValue
from omero.rtypes import rstring

NS_COLLECTION = "ome/collection"
NS_NODE = "ome/collection/nodes"


def create_collection(conn, name, version="0.x"):
    """
    Create a collection annotation (not linked to any image yet).
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

    # Save to server
    update_service = conn.getUpdateService()
    saved = update_service.saveAndReturnObject(map_annotation)

    return saved.getId().getValue()


def link_collection_to_image(conn, collection_ann_id, image_id):
    """Link an existing collection annotation to an image."""
    image = conn.getObject("Image", image_id)
    annotation = conn.getObject("MapAnnotation", collection_ann_id)

    if image is None:
        raise ValueError("Image {} not found".format(image_id))
    if annotation is None:
        raise ValueError("Annotation {} not found".format(collection_ann_id))

    image.linkAnnotation(annotation)


def add_node_annotation(conn, image_id, node_type, collection_ann_id, 
                        node_name=None, attributes=None):
    """
    Add a node annotation to an image describing its role in the collection.
    """
    kv = {
        "type": node_type,
        "collection_id": str(collection_ann_id)
    }
    if node_name:
        kv["name"] = node_name
    if attributes:
        for key, value in attributes.items():
            kv["attributes.{}".format(key)] = str(value)

    return ezomero.post_map_annotation(conn, "Image", image_id, kv, ns=NS_NODE)


def get_collection_members(conn, collection_ann_id):
    """Get all images linked to a collection annotation."""
    images = conn.getObjectsByAnnotations("Image", [collection_ann_id])
    return [img.getId() for img in images]


def get_collections(conn, image_id):
    """
    Get all collections an image is part of.
    Returns a list of dicts, each with collection metadata and all member images.
    Returns empty list if image is not part of any collection.
    """
    coll_ann_ids = ezomero.get_map_annotation_ids(conn, "Image", image_id, ns=NS_COLLECTION)

    collections = []
    for coll_ann_id in coll_ann_ids:
        coll_info = ezomero.get_map_annotation(conn, coll_ann_id)

        # Get all members and their node info
        member_ids = get_collection_members(conn, coll_ann_id)
        members = []
        for member_id in member_ids:
            node_info = get_node_info(conn, member_id)
            members.append({
                "image_id": member_id,
                "nodes": node_info
            })

        collections.append({
            "collection_id": coll_ann_id,
            "name": coll_info.get("name"),
            "version": coll_info.get("version"),
            "members": members
        })

    return collections


def get_node_info(conn, image_id):
    """Get the node annotation info for an image."""
    ann_ids = ezomero.get_map_annotation_ids(conn, "Image", image_id, ns=NS_NODE)
    for ann_id in ann_ids:
        return ezomero.get_map_annotation(conn, ann_id)
    return None


def find_related_images(conn, image_id, node_type=None):
    """
    Given an image, find all related images in the same collection(s).
    Optionally filter by node_type (e.g., "label", "multiscale").
    """
    # Find collection annotations on this image
    coll_ann_ids = ezomero.get_map_annotation_ids(conn, "Image", image_id, ns=NS_COLLECTION)

    related = []
    for coll_ann_id in coll_ann_ids:
        member_ids = get_collection_members(conn, coll_ann_id)
        for member_id in member_ids:
            if member_id == image_id:
                continue
            node_info = get_node_info(conn, member_id)
            if node_info:
                if node_type is None or node_info.get("type") == node_type:
                    related.append({
                        "image_id": member_id,
                        "collection_id": coll_ann_id,
                        "nodes": node_info
                    })

    return related
