import argparse
import imageio.v3 as imageio

from skimage.measure import label

from biohack_utils.util import connect_to_omero, _upload_image, _upload_volume


def upload_data(conn, fpath, name, labels=False):
    """Upload image or label data.

    Args:
        conn: BlitzGateway conection to omero.web.
        fpath: File path to data.
        name: Name for uploaded data.
        labels: Specify uploaded data as labels to set data type to uint16.
    """
    arr = imageio.imread(fpath)
    if labels:
        arr = label(arr).astype("uint16")

    if len(arr.shape) == 2:
        img_id = _upload_image(conn, arr, name)

    elif len(arr.shape) == 3:
        img_id = _upload_volume(conn, arr, name)

    else:
        raise ValueError("Input data must have 2D or 3D shape.")

    print(f"Created image with ID: {img_id}")


def main():
    parser = argparse.ArgumentParser(
        description="Upload_ ata to Omero web.")

    parser.add_argument("-u", "--username", type=str, required=True)
    parser.add_argument("-p", "--password", type=str, required=True)

    parser.add_argument("-i", "--input", type=str, required=True)
    parser.add_argument("-n", "--name", type=str, required=True,
                        help="Name of uploaded data on Omero.")

    parser.add_argument(
        "--label", action="store_true",
        help="Specify that the uploaded data is a label. Default: Image data."
    )

    args = parser.parse_args()

    conn = connect_to_omero(args)
    upload_data(conn, args.input, args.name, args.label)

    conn.close()


if __name__ == "__main__":
    main()
