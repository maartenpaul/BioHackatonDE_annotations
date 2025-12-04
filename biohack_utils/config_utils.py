from biohack_utils.ConfigSchema import OMECollection, OMEWrapper, CollectionNode, NodeAttributes, MultiscaleNode, NS_COLLECTION, NS_NODE
from omero.rtypes import rstring
from omero.model import MapAnnotationI, NamedValue
from biohack_utils.ConfigSchema import OMECollection, OMEWrapper, CollectionNode, NodeAttributes, MultiscaleNode, NS_COLLECTION, NS_NODE
import omero.sys
from biohack_utils.omero_annotation import _create_collection, _link_collection_to_image, _add_node_annotation, _build_image_url, _append_link_to_node_annotation 


NS_COLLECTION = "ome/collection"
NS_NODE = "ome/collection/nodes"

def flatten(wrapper: OMEWrapper) -> list[dict]:
    """Convert nested JSON to flat list with paths."""
    result = []
    
    def traverse(nodes, prefix=""):
        for node in nodes:
            path = f"{prefix}/{node.name}" if prefix else node.name
            
            if isinstance(node, CollectionNode):
                traverse(node.nodes, path)
            else:
                record = {'path': path}
                record.update(node.attributes.model_dump(by_alias=True, exclude_none=True))
                result.append(record)
    
    traverse(wrapper.ome.nodes)
    return result


def unflatten(flat_records: list[dict], name: str, version: str = "0.x") -> OMEWrapper:
    """Convert flat list back to nested JSON."""
    collections = {}
    root_nodes = []
    
    for record in sorted(flat_records, key=lambda x: x['path'].count('/')):
        path = record['path']
        parts = path.split('/')
        node_name = parts[-1]
        parent_path = '/'.join(parts[:-1]) if len(parts) > 1 else None
        
        # Create node
        attrs = {k: v for k, v in record.items() if k != 'path'}
        node = MultiscaleNode(name=node_name, attributes=NodeAttributes(**attrs))
        
        # Create parent collections if needed
        for depth in range(1, len(parts)):
            coll_path = '/'.join(parts[:depth])
            if coll_path not in collections:
                coll = CollectionNode(name=parts[depth-1], nodes=[])
                collections[coll_path] = coll
                if depth == 1:
                    root_nodes.append(coll)
                else:
                    collections['/'.join(parts[:depth-1])].nodes.append(coll)
        
        # Add node
        if parent_path:
            collections[parent_path].nodes.append(node)
        else:
            root_nodes.append(node)
    
    return OMEWrapper(ome=OMECollection(version=version, name=name, nodes=root_nodes))


def upload(conn, wrapper: OMEWrapper) -> int:
    """Upload collection to OMERO. Returns collection_id."""

    
    # Create collection annotation
    coll_ann = MapAnnotationI()
    coll_ann.setNs(rstring(NS_COLLECTION))
    coll_ann.setMapValue([
        NamedValue("version", wrapper.ome.version),
        NamedValue("name", wrapper.ome.name)
    ])
    coll_id = conn.getUpdateService().saveAndReturnObject(coll_ann).getId().getValue()
    
    # Process each node
    for record in flatten(wrapper):
        image_id = record['omero:image_id']
        image = conn.getObject("Image", image_id)
        
        # Link collection annotation
        image.linkAnnotation(conn.getObject("MapAnnotation", coll_id))
        
        # Create node annotation
        node_kv = {'path': record['path'], 'collection_id': str(coll_id)}
        for key, val in record.items():
            if key not in ('path', 'omero:image_id'):
                if isinstance(val, list):
                    val = ','.join(str(v) for v in val)
                node_kv[key] = str(val)
        
        node_ann = MapAnnotationI()
        node_ann.setNs(rstring(NS_NODE))
        node_ann.setMapValue([NamedValue(k, v) for k, v in node_kv.items()])
        node_id = conn.getUpdateService().saveAndReturnObject(node_ann).getId().getValue()
        image.linkAnnotation(conn.getObject("MapAnnotation", node_id))
    
    return coll_id


#Some issue with the python API requires us to use a query here
def download(conn, collection_id: int) -> OMEWrapper:
    """Download collection from OMERO."""
    
    # Get collection metadata
    coll_ann = conn.getObject("MapAnnotation", collection_id)
    if coll_ann is None:
        raise ValueError(f"Collection annotation {collection_id} not found")
    
    coll_data = {kv.name: kv.value for kv in coll_ann.getMapValue()}
    
    # Get all images with this collection
    images = list(conn.getObjectsByAnnotations("Image", [collection_id]))
    
    flat_records = []
    for img in images:
        image_id = img.getId()
        print(f"\nProcessing image {image_id}")
        
        # Force reload of annotations by getting a fresh image object
        fresh_img = conn.getObject("Image", image_id)
        
        # Try getting MapAnnotations specifically with the node namespace
        params = omero.sys.ParametersI()
        params.addId(image_id)
        
        query = """
            SELECT ann FROM ImageAnnotationLink link
            JOIN link.child ann
            JOIN link.parent img
            WHERE img.id = :id
            AND ann.class = MapAnnotation
            AND ann.ns = :ns
        """
        
        params.addString("ns", NS_NODE)
        
        query_service = conn.getQueryService()
        results = query_service.findAllByQuery(query, params, conn.SERVICE_OPTS)
        
        print(f"  Found {len(results)} node annotations via query")
        
        for ann_obj in results:
            # Wrap in gateway object for easier handling
            ann = conn.getObject("MapAnnotation", ann_obj.getId().getValue())
            
            node_data = {kv.name: kv.value for kv in ann.getMapValue()}
            
            # Verify this node belongs to our collection
            if node_data.get('collection_id') != str(collection_id):
                continue
            
            print(f"  ✓ Match found!")
            
            # Build record
            record = {'omero:image_id': image_id, 'path': node_data['path']}
            
            # Extract attributes
            for key, val in node_data.items():
                if key not in ('path', 'collection_id'):
                    if ',' in val:
                        record[key] = val.split(',')
                    else:
                        record[key] = val
            
            flat_records.append(record)
            break  # Only process first matching annotation per image
    
    print(f"\nTotal flat records collected: {len(flat_records)}")
    
    if not flat_records:
        raise ValueError(f"No node annotations found for collection {collection_id}")
    
    return unflatten(flat_records, coll_data['name'], coll_data.get('version', '0.x'))


def write_annotations_to_image_and_labels(conn, image_id, label_id):
    # Creates a new collection
    ann_id = _create_collection(conn, "cells", "0.0.1")
    
    if isinstance(image_id, int):
        image_id = [image_id]
    
    for curr_iid in image_id:
        # Link the collection to the raw image
        _link_collection_to_image(conn, ann_id, curr_iid)
        
        # Add node annotation - new style with our schema
        _add_node_annotation(
            conn, curr_iid, 
            node_type="intensities",  # Not really used, but kept for signature
            collection_ann_id=ann_id,
            node_name="raw",  # This becomes the path
            attributes={
                "category": "intensities",
                "origin": "raw",
                "description": "Raw image data"
            }
        )
    
    # Link the collection to the label image
    _link_collection_to_image(conn, ann_id, label_id)
    
    # Add node annotation to the label image
    _add_node_annotation(
        conn, label_id,
        node_type="annotations",
        collection_ann_id=ann_id,
        node_name="cell_segmentation",  # This becomes the path
        attributes={
            "category": "annotations",
            "origin": "masks",
            "source": "raw",  # References the raw image by path
            "description": "Cell segmentation results"
        }
    )
    
    # Build pseudo-network by linking all images
    all_image_ids = image_id + [label_id]
    for iid in all_image_ids:
        link = _build_image_url(iid)
        _append_link_to_node_annotation(conn, iid, link)