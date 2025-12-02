# BioHackaton DE 2025

This repository was created within the project [**Integrating Data Science Capabilities within the OMERO Data Management Ecosystem**](https://www.denbi.de/de-nbi-events/1936-4th-biohackathon-germany-integrating-data-science-capabilities-within-the-omero-data-management-ecosystem) during the [**4th BioHackathon Germany**](https://www.denbi.de/de-nbi-events/1840-4th-biohackathon-germany), which was held from 01-05 December 2025 in Walsrode, Germany.

The goal of this project is to design and prototype a standardized way to integrate **label data** into the OMERO data management ecosystem. The work is explicitly aligned with the **OME-Zarr RFC-8 specification on collections** and explores how this concept can be adapted to connect images with label images in a structured way, e.g. through key-value pairs.

---

## Motivation

In the current OMERO data model, label and segmentation data are typically represented as **ROIs (regions of interest)** that are attached to a reference image. While this works well for sparse vector-style annotations, it is limiting for:

* Dense pixel-wise segmentations
* Multiple competing or alternative segmentations of the same image
* Machine-learning-generated label images
* Rich provenance tracking of label generation

At the same time, the OME-Zarr ecosystem is moving toward a more explicit and scalable representation of image relationships via **collections**, as described in RFC-8. This repository explores how this concept can be transferred to OMERO to enable:

* First-class support for label images
* Structured grouping of related labels
* Interoperability with OME-Zarr-based analysis pipelines
* Clear separation between raw images and derived label products

---

## Project Goals

The main goals of this project are:

1. **Define a data model for label collections in OMERO**

   * Represent label images as first-class objects
   * Group related label images into collections linked to a reference image

2. **Align OMERO with OME-Zarr RFC-8**

   * Reuse the core concepts of collections
   * Ensure conceptual and structural compatibility with OME-Zarr

3. **Enable provenance-aware label management**

   * Track how each label image was generated (manual, ML, algorithm, version)
   * Support multiple segmentation versions per image

4. **Provide a prototype implementation**

   * Demonstrate how label collections can be stored, linked, queried, and visualized in OMERO

---

## Concept: Label Collections for a Single Image

This repository proposes to adapt the RFC-8 collection model to the specific use case of **label collections bound to a reference image**.

### Core Entities

* **Reference Image**
  The original raw image stored in OMERO.

* **Label Image**
  A derived image where pixel values represent categorical or instance labels (e.g., segmentation masks).

* **Label Collection**
  A logical grouping of multiple label images that all refer to the same reference image.

### Relationships

* One **Reference Image** → many **Label Collections**
* One **Label Collection** → many **Label Images**
* Each **Label Image** → exactly one **Reference Image**

This allows multiple independent segmentation experiments (manual, automated, multiscale, time-stamped, etc.) to coexist without ambiguity.

### Metadata and Provenance

Each label image and collection should carry structured metadata, for example:

* Algorithm or annotation method
* Software name and version
* Author / creator
* Creation timestamp
* Label schema (class names, IDs, colors)
* Training dataset or model hash (for ML-generated labels)

---

## Adapting RFC-8 Collections to OMERO

RFC-8 defines collections as structured containers for grouping related data. For OMERO, the following adaptations are proposed:

### 1. Mapping Collections to OMERO Objects

We recommend creating a new custom collection type because *OMERO Projects* and *OMERO Datasets* are already established concepts, which limits their adaptability for this use case.

### 2. Linking via Key-Value Annotations

Reference images and label images should be linked using structured key-value annotations, for example:

* `omero.ref_image_id = <ID>`
* `omero.collection_id = <ID>`
* `label.type = semantic | instance | panoptic`
* `label.version = v1.0`

This enables robust programmatic resolution of relationships.

### 3. Instance-Level Identity

Each segmentation instance (e.g., each object mask) should be assigned a stable OMERO identifier to:

* Enable cross-dataset referencing
* Support tracking across time or versions
* Allow linking to tabular feature data

### 4. Compatibility with OME-Zarr

The mapping should ensure that:

* Label images exported to OME-Zarr preserve their collection structure
* OME-Zarr collections can be re-imported into OMERO without loss of semantics
* Metadata fields align with RFC-8 where possible

---

## OMERO Annotations

This repository investigates improved usage of OMERO annotations for label data, including:

* Structured key-value pairs for linking images and labels
* Controlled vocabularies for label types and methods
* JSON-based metadata payloads for complex label schemas

The aim is to move from ad-hoc ROI usage toward a **formal label-image model** with rich semantics.

---

## Repository Scope

This repository currently focuses on:

* Conceptual data modeling
* Prototypical scripts and services
* Demonstration datasets
* Export/import experiments with OME-Zarr

It is **not** intended to be a production-ready OMERO plugin at this stage.

---

## Installation

This project uses **pixi** for environment and dependency management.

1. Install pixi:
   [https://pixi.sh/latest/installation/](https://pixi.sh/latest/installation/)

2. Install dependencies:

```bash
pixi install
```

---

## Roadmap (Draft)

* [ ] Formal definition of the label collection data model
* [ ] Prototype mapping to OMERO Projects/Datasets
* [ ] Key-value annotation schema
* [ ] OME-Zarr export of label collections
* [ ] OME-Zarr import into OMERO
* [ ] Example visualization in OMERO.web

---

## Contributing

Contributions are welcome in the form of:

* Conceptual discussions and issues
* Data model proposals
* Prototype implementations
* Test datasets and use cases

Please open an issue or pull request to get involved.

---

## License

License information will be added once the scope of the prototype is finalized.
