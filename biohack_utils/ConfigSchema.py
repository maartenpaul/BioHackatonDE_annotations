from typing import Optional, Union, Literal
from pydantic import BaseModel, Field, model_validator

IntensityOrigin = Literal["raw", "processed"]
AnnotationOrigin = Literal["masks", "tracks", "shapes", "points"]

class NodeAttributes(BaseModel):
    omero_image_id: int = Field(alias="omero:image_id")
    category: Literal["intensities", "annotations"]
    origin: Union[IntensityOrigin, AnnotationOrigin]
    source: Optional[Union[str, list[str]]] = None
    description: Optional[str] = None
    
    class Config:
        populate_by_name = True
        extra = "allow"
    
    @model_validator(mode="after")
    def validate_category_origin_source(self):
        if self.category == "intensities" and self.origin not in ("raw", "processed"):
            raise ValueError("Intensities must have origin: raw or processed")
        if self.category == "annotations" and self.origin not in ("masks", "tracks", "shapes", "points"):
            raise ValueError("Annotations must have origin: masks, tracks, shapes, or points")
        
        is_derived = self.origin != "raw"
        if is_derived and self.source is None:
            raise ValueError(f"Source required for origin '{self.origin}'")
        if not is_derived and self.source is not None:
            raise ValueError("Raw intensities should not have a source")
        
        return self


class MultiscaleNode(BaseModel):
    type: Literal["multiscale"] = "multiscale"
    name: str
    attributes: NodeAttributes


class CollectionNode(BaseModel):
    type: Literal["collection"] = "collection"
    name: str
    nodes: list[Union["CollectionNode", MultiscaleNode]]

CollectionNode.model_rebuild()

class OMECollection(BaseModel):
    version: str = "0.x"
    type: Literal["collection"] = "collection"
    name: str
    nodes: list[Union[CollectionNode, MultiscaleNode]]

class OMEWrapper(BaseModel):
    ome: OMECollection