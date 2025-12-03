from biohack_utils.omero_annotation import _get_collection_members, _get_node_info
from biohack_utils.CollectionModel import OMECollection, MultiscaleNode, NodeAttributes, OMEROInfo, LabelInfo

def get_collection_as_model(conn, collection_ann_id: int) -> OMECollection:
    """Read OMERO annotations and return validated Pydantic model."""
    
    # Parse collection annotation
    coll_info = {}
    map_annotation = conn.getObject('MapAnnotation', collection_ann_id).getValue()
    for item in map_annotation:
        if item[0] in coll_info:
            if not isinstance(coll_info[item[0]], list):
                coll_info[item[0]] = [coll_info[item[0]]]
            coll_info[item[0]].append(item[1])
        else:
            coll_info[item[0]] = item[1]

    member_ids = _get_collection_members(conn, collection_ann_id)
    
    nodes = []
    for image_id in member_ids:
        node_info = _get_node_info(conn, image_id)
        
        if node_info is None:
            node_info = {}
        
        node_type = node_info.get("type", "intensities").lower()
        node_name = node_info.get("name", "image_{}".format(image_id))
        
        # Build attributes
        attrs = NodeAttributes(omero=OMEROInfo(image_id=image_id))
        
        if node_type == "labels":
            # Parse source - could be comma-separated for multiple sources
            source_str = node_info.get("label.source") or node_info.get("source")
            source = None
            if source_str:
                source = source_str.split(",") if "," in source_str else source_str
            attrs.label = LabelInfo(source=source)
        
        nodes.append(MultiscaleNode(name=node_name, attributes=attrs))
    
    return OMECollection(
        version=coll_info.get("version", "0.x"),
        name=coll_info.get("name", "unnamed"),
        nodes=nodes
    )