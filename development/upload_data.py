import argparse
import imageio.v3 as imageio

from skimage.measure import label

from biohack_utils.util import connect_to_omero


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
        arr = label(labels).astype("uint16")

    def _upload_image(curr, iname):
        images = [curr]
        image = conn.createImageFromNumpySeq(
            (im for im in images),
            imageName=iname,
        )
        print(f"Created image with ID: {image.id}")

    def _upload_volume(curr, iname):
        # Upload the image and corresponding labels
        im = conn.createImageFromNumpySeq(
            (plane for plane in curr),
            sizeZ=curr.shape[0],
            sizeC=1,
            sizeT=1,
            imageName=iname,
        )
        print(f"Created image with ID: {im.id}")

    if len(arr.shape) == 3:
        _upload_image(arr, name)

    if len(arr.shape) == 3:
        _upload_volume(arr, name)


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
    upload_data(conn, args.input, args.description, args.label)

    conn.close()


if __name__ == "__main__":
    main()
