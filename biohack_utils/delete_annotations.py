from .util import connect_to_omero, omero_credential_parser


def delete_annotations(conn, image_id, ns):
    image = conn.getObject("Image", image_id)

    anns = list(image.listAnnotations(ns=ns))

    fanns = []
    for ann in anns:
        kv_dict = {k: v for k, v in ann.getValue()}
        print("Annotation ID:", ann.getId())
        print(kv_dict)
        fanns.append(ann.getId())

    conn.deleteObjects("Annotation", fanns, wait=True)


def main():
    parser = omero_credential_parser()
    args = parser.parse_args()

    conn = connect_to_omero(args)

    try:
        delete_annotations(conn, args.image_id, args.namespace)
    except AttributeError:
        print("Well, seems like there were no matching collection metadata.")

    conn.close()
