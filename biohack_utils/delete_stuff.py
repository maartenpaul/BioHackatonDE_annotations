from .util import connect_to_omero, omero_credential_parser


def _delete_anns(conn, image_id: int, ns: str):
    image = conn.getObject("Image", image_id)

    anns = list(image.listAnnotations(ns=ns))

    fanns = []
    for ann in anns:
        kv_dict = {k: v for k, v in ann.getValue()}
        print("Annotation ID:", ann.getId())
        print(kv_dict)
        fanns.append(ann.getId())

    conn.deleteObjects("Annotation", fanns, wait=True)


def delete_annotations():
    parser = omero_credential_parser()
    args = parser.parse_args()

    conn = connect_to_omero(args)

    try:
        _delete_anns(conn, args.image_id, args.namespace)
    except AttributeError:
        print("Well, seems like there were no matching collection metadata.")

    conn.close()


def _delete_ims(conn, image_id: int):
    img = conn.getObject("Image", image_id)
    if img is None:
        print(f"Image {image_id} already gone, skipping.")
    else:
        conn.deleteObjects("Image", [image_id], wait=True)


def delete_images():
    parser = omero_credential_parser()
    args = parser.parse_args()

    conn = connect_to_omero(args)

    _delete_ims(conn, args.image_id)
    # print("Well, seems like there were no matching image for the given ids.")

    conn.close()
