import imageio.v3 as imageio
from skimage.measure import label

from biohack_utils.util import omero_credential_parser, connect_to_omero


def upload_images(conn):
    # Get the CochleaNet image and labels.
    image = imageio.imread("/home/anwai/data/M_LR_000167_R_crop_1137-0669-1044.tif")
    labels = imageio.imread("/home/anwai/data/M_LR_000167_R_crop_1137-0669-1044_annotations.tif")

    # Run connected components and reduce precision
    labels = label(labels).astype("uint16")

    def _upload_volume(curr, desc):
        # Upload the image and corresponding labels
        im = conn.createImageFromNumpySeq(
            (plane for plane in curr),
            sizeZ=curr.shape[0],
            sizeC=1,
            sizeT=1,
            imageName=desc,
        )
        print(f"Created image with ID: {im.id}")

    _upload_volume(image, "Cochlea_Neurons")
    _upload_volume(labels, "Neuron_Segmentation")


def main():
    parser = omero_credential_parser()
    args = parser.parse_args()

    conn = connect_to_omero(args)

    upload_images(conn)

    conn.close()


if __name__ == "__main__":
    main()
