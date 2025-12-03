from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal, Union, Annotated

class LabelInfo(BaseModel):
    """
    Marks this node as a label image.
    Presence of this attribute = node is a label.
    """
    source: Optional[Union[str, list[str]]] = None

class OMEROInfo(BaseModel):
    """OMERO identifiers."""
    image_id: int
    dataset_id: Optional[int] = None

class NodeAttributes(BaseModel):
    """Node attributes following RFC-8 pattern."""
    label: Optional[LabelInfo] = None
    omero: Optional[OMEROInfo] = None
    
    class Config:
        extra = "allow"

class MultiscaleNode(BaseModel):
    """An OME-Zarr multiscale image."""
    type: Literal["multiscale"] = "multiscale"
    name: str
    path: Optional[str] = None
    attributes: Optional[NodeAttributes] = None
    
    def is_label(self) -> bool:
        return self.attributes is not None and self.attributes.label is not None
    
    def get_sources(self) -> list[str]:
        """Get source node names if this is a label."""
        if not self.is_label():
            return []
        source = self.attributes.label.source
        if source is None:
            return []
        return source if isinstance(source, list) else [source]

class CollectionNode(BaseModel):
    """Groups nodes together."""
    type: Literal["collection"] = "collection"
    name: str
    nodes: Optional[list[Union["CollectionNode", MultiscaleNode]]] = None
    path: Optional[str] = None
    attributes: Optional[dict] = None
    
    @model_validator(mode="after")
    def check_nodes_or_path(self):
        if self.nodes is not None and self.path is not None:
            raise ValueError("Cannot have both 'nodes' and 'path'")
        return self

CollectionNode.model_rebuild()

Node = Annotated[
    Union[CollectionNode, MultiscaleNode],
    Field(discriminator="type")
]

class OMECollection(BaseModel):
    """Root collection."""
    version: str = "0.x"
    type: Literal["collection"] = "collection"
    name: str
    nodes: list[Node]
    attributes: Optional[dict] = None
    
    def get_intensity_nodes(self) -> list[MultiscaleNode]:
        """Get all non-label multiscale nodes (flat, not recursive)."""
        return [n for n in self.nodes 
                if isinstance(n, MultiscaleNode) and not n.is_label()]
    
    def get_label_nodes(self) -> list[MultiscaleNode]:
        """Get all label nodes (flat, not recursive)."""
        return [n for n in self.nodes 
                if isinstance(n, MultiscaleNode) and n.is_label()]
    
    def get_node_by_name(self, name: str) -> Optional[MultiscaleNode]:
        """Find a node by name."""
        for n in self.nodes:
            if isinstance(n, MultiscaleNode) and n.name == name:
                return n
        return None

class OMEWrapper(BaseModel):
    """Top-level wrapper."""
    ome: OMECollection