import argparse
import logging
import math
import os
from pathlib import Path
import random
import shutil
from typing import Dict, List

from tqdm import tqdm

_FORMAT_EXTENSIONS = {
    "coco": ".json",
    "darknet": ".txt",
    "kitti": ".txt",
    "openimages": ".csv",
    "pascal": ".xml",
}


# ------------------------------------------------------------------------------
# set up a basic, global _logger which will write to the console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d  %H:%M:%S",
)
_logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
def split_ids_train_valid(
        ids: List[str],
        train_pct: float,
) -> (List[str], List[str]):
    """
    Split a list of IDs into two lists based on a split percentage value.
    (IDs are shuffled before splitting in order to get a random order.)

    :param ids: list of ID strings
    :param train_pct: percentage between 0.0 and 1.0
    :return: two lists of IDs split from the original list based on the training
        percentage with the first list containing train_pct and the second
        containing (1 - train_pct)
    """

    # get the split based on the number of matching IDs and split percentage
    split_index = int(round(train_pct * len(ids)))
    random.shuffle(ids)
    training_ids = ids[:split_index]
    validation_ids = ids[split_index:]

    return training_ids, validation_ids


# ------------------------------------------------------------------------------
def map_ids_to_paths(
        directory: str,
        extensions: List[str],
) -> Dict:
    """
    For all files in a directory that end with the specified extension(s) we map
    the file IDs to the full file paths.

    For example, if we have a directory with the following files:

    /home/ubuntu/img1.jpg
    /home/ubuntu/img2.png
    /home/ubuntu/img3.jpg

    Then map_ids_to_paths("home/ubuntu", [".jpg"]) results in the following
    dictionary:

    { "img1": "/home/ubuntu/img1.jpg", "img3": "/home/ubuntu/img3.jpg",}

    :param directory:
    :param extensions:
    :return:
    """

    # list the files in the directory
    files = os.listdir(directory)
    file_paths = [os.path.join(directory, f) for f in files]

    # build dictionary with file IDs as keys and file paths as values
    ids_to_paths = {}

    for ext in extensions:
        for file_path in file_paths:
            if os.path.isfile(file_path) and file_path.endswith(ext):
                ids_to_paths[Path(file_path).stem] = file_path

    return ids_to_paths


# ------------------------------------------------------------------------------
def create_split_files(
        images_dir: str,
        use_prefix: str,
        dest_dir: str,
        train_pct: float,
) -> (str, str):
    """
    Creates two text files, train.txt and valid.txt, in the specified destination
    directory, with each file containing lines specifying the image files of the
    training or validation dataset relative to the images directory.

    We assume that the resulting files will be used for training Darknet-based
    models and hence we expect the annotation extension to be *.txt.

    :param images_dir: directory that contains the images we'll split into
        training and validation sets
    :param use_prefix: the relative file path prefix to prepend to the file name
        when writing lines in the train.txt and valid.txt output files
    :param dest_dir: directory where the train.txt and valid.txt should be written
    :param train_pct: value between 0.0 and 1.0 indicating the training percentage
        (validation percentage = 1.0 - training percentage)
    :return:
    """

    # map the file IDs to their corresponding full paths
    for img_ext in (".jpg", ".png"):

        images = map_ids_to_paths(images_dir, [img_ext])
        annotations = map_ids_to_paths(images_dir, [".txt"])

        # find matching image/annotation file IDs
        ids = list(set(images.keys()).intersection(annotations.keys()))

        # split the file IDs into training and validation lists
        training_ids, validation_ids = split_ids_train_valid(ids, train_pct)

        # create the destination directory in case it doesn't already exist
        os.makedirs(dest_dir, exist_ok=True)

        # write the relative file paths for the training images into train.txt
        train_file_path = os.path.join(dest_dir, "train.txt")
        with open(train_file_path, "w+") as train_file:
            for img_id in training_ids:
                train_file.write(os.path.join(use_prefix, img_id + img_ext) + "\n")

        # write the relative file paths for the validation images into valid.txt
        valid_file_path = os.path.join(dest_dir, "valid.txt")
        with open(valid_file_path, "w+") as valid_file:
            for img_id in validation_ids:
                valid_file.write(os.path.join(use_prefix, img_id + img_ext) + "\n")

    return train_file_path, valid_file_path


# ------------------------------------------------------------------------------
def _split_files(
        copy_files: bool,
        file_ids: List[str],
        annotation_paths: Dict,
        annotations_dest_dir: str,
        image_paths: Dict,
        images_dest_dir: str,
) -> int:
    """
    TODO

    :param copy_files: whether or not to copy the files (move files if false)
    :param file_ids: file IDs for annotation and image files to be copied/moved
    :param annotation_paths: dictionary of file IDs to annotation file paths
    :param annotations_dest_dir: destination directory for annotation files
    :param image_paths: dictionary of file IDs to image file paths
    :param images_dest_dir: destination directory for image files
    :return: 0 indicates success
    """

    def relocate_file(copy_file: bool, src_file_path: str, dest_dir: str):
        """
        TODO

        :param copy_file whether or not to copy the files (move files if false)
        :param src_file_path: absolute path of source file to be copied
        :param dest_dir: destination directory for the file copy
        :return: 0 indicates success
        """

        file_name = os.path.basename(src_file_path)
        dest_file_path = os.path.join(dest_dir, file_name)
        if copy_file:
            shutil.copy2(src_file_path, dest_file_path)
        else:
            shutil.move(src_file_path, dest_file_path)
        return 0

    # copy or move the image and annotation files into the destination directories
    for file_id in tqdm(file_ids):
        relocate_file(copy_files, annotation_paths[file_id], annotations_dest_dir)
        relocate_file(copy_files, image_paths[file_id], images_dest_dir)

    return 0


# ------------------------------------------------------------------------------
def split_train_valid_test(split_arguments: Dict):

    # create the training, validation, and testing
    # directories if they don't already exist
    os.makedirs(split_arguments["train_annotations_dir"], exist_ok=True)
    os.makedirs(split_arguments["val_annotations_dir"], exist_ok=True)
    os.makedirs(split_arguments["test_annotations_dir"], exist_ok=True)
    os.makedirs(split_arguments["train_images_dir"], exist_ok=True)
    os.makedirs(split_arguments["val_images_dir"], exist_ok=True)
    os.makedirs(split_arguments["test_images_dir"], exist_ok=True)

    # map the file IDs to their corresponding full paths
    images = map_ids_to_paths(split_arguments["images_dir"], [".jpg", ".png"])
    annotations = map_ids_to_paths(
        split_arguments["annotations_dir"],
        [_FORMAT_EXTENSIONS[split_arguments["format"]]],
    )

    # find matching image/annotation file IDs
    ids = list(set(images.keys()).intersection(annotations.keys()))

    # split the file IDs into training and validation lists
    # get the split based on the number of matching IDs and split percentages
    final_train_index = int(round(split_arguments["train_percentage"] * len(ids)))
    final_valid_index = \
        int(round((split_arguments["train_percentage"] +
                   split_arguments["valid_percentage"]) * len(ids)
                  )
            )
    random.shuffle(ids)
    training_ids = ids[:final_train_index]
    validation_ids = ids[final_train_index:final_valid_index]
    testing_ids = ids[final_valid_index:]

    # copy images and annotations into the training directories
    _logger.info("Splitting files for the training set into "
                 f"{split_arguments['train_images_dir']} "
                 f"and {split_arguments['train_annotations_dir']}")
    _split_files(
        split_arguments["copy_feature"],
        training_ids,
        annotations,
        split_arguments["train_annotations_dir"],
        images,
        split_arguments["train_images_dir"]
    )

    # copy images and annotations into the validation directories
    _logger.info("Splitting files for the validation set into "
                 f"{split_arguments['val_images_dir']} "
                 f"and {split_arguments['val_annotations_dir']}")
    _split_files(
        split_arguments["copy_feature"],
        validation_ids,
        annotations,
        split_arguments["val_annotations_dir"],
        images,
        split_arguments["val_images_dir"]
    )

    # copy images and annotations into the testing directories
    _logger.info("Splitting files for the testing set into "
                 f"{split_arguments['test_images_dir']} "
                 f"and {split_arguments['test_annotations_dir']}")
    _split_files(
        split_arguments["copy_feature"],
        testing_ids,
        annotations,
        split_arguments["test_annotations_dir"],
        images,
        split_arguments["test_images_dir"]
    )


# ------------------------------------------------------------------------------
if __name__ == "__main__":
    """
    Usage:
    $ python split.py \
        --annotations_dir /data/datasets/handgun/pascal \
        --images_dir /data/datasets/handgun/images \
        --train_annotations_dir /data/datasets/handgun/pascal/train \
        --train_images_dir /data/datasets/handgun/images/train \
        --val_annotations_dir /data/datasets/handgun/pascal/valid \
        --val_images_dir /data/datasets/handgun/images/valid \
        --test_annotations_dir /data/datasets/handgun/pascal/test \
        --test_images_dir /data/datasets/handgun/images/test \
        --format pascal
    """

    # parse the command line arguments
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument(
        "--annotations_dir",
        required=True,
        type=str,
        help="path to directory containing "
             "PASCAL VOC annotation XML files",
    )
    args_parser.add_argument(
        "--images_dir",
        required=True,
        type=str,
        help="path to directory containing image files",
    )
    args_parser.add_argument(
        "--train_annotations_dir",
        required=True,
        type=str,
        help="path to new directory containing "
             "PASCAL VOC annotation XML files for training",
    )
    args_parser.add_argument(
        "--train_images_dir",
        required=True,
        type=str,
        help="path to new directory containing image "
             "files for training",
    )
    args_parser.add_argument(
        "--val_annotations_dir",
        required=True,
        type=str,
        help="path to new directory containing PASCAL "
             "VOC annotation XML files for validation",
    )
    args_parser.add_argument(
        "--val_images_dir",
        required=True,
        type=str,
        help="path to new directory containing image "
             "files for validation",
    )
    args_parser.add_argument(
        "--test_annotations_dir",
        required=True,
        type=str,
        help="path to new directory containing "
             "PASCAL VOC annotation XML files for testing",
    )
    args_parser.add_argument(
        "--test_images_dir",
        required=True,
        type=str,
        help="path to new directory containing image "
             "files for testing",
    )
    args_parser.add_argument(
        "--train_percentage",
        required=False,
        type=float,
        default=0.7,
        help="percentage of files to use for training "
             "(value should be between 0.0 and 1.0)",
    )
    args_parser.add_argument(
        "--valid_percentage",
        required=False,
        type=float,
        default=0.2,
        help="percentage of files to use for validation "
             "(value should be between 0.0 and 1.0)",
    )
    args_parser.add_argument(
        "--test_percentage",
        required=False,
        type=float,
        default=0.1,
        help="percentage of files to use for training "
             "(value should be between 0.0 and 1.0)",
    )
    args_parser.add_argument(
        "--format",
        type=str,
        required=False,
        default="pascal",
        choices=["darknet", "coco", "kitti", "pascal", ],
        help="output format: KITTI, PASCAL, Darknet, TFRecord, or COCO",
    )
    # add an option that defaults to copying files, otherwise files will be moved
    args_parser.add_argument(
        "--copy",
        dest="copy_feature",
        action="store_true",
        help="Copy files, leaving the originals in place"
    )
    args_parser.add_argument(
        "--no_copy",
        dest="copy_feature",
        action="store_false",
        help="Move the files",
    )
    args_parser.set_defaults(copy_feature=True)
    args = vars(args_parser.parse_args())

    # confirm that the percentages all add to 100%
    total_percentage = \
        float(args["train_percentage"]) + \
        float(args["valid_percentage"]) + \
        float(args["test_percentage"])
    if not math.isclose(1.0, total_percentage):
        raise ValueError(
            "Invalid argument values: the combined train/valid/test "
            "percentages do not add to 1.0"
        )

    # split files from the images and annotations
    # directories into training and validation sets
    split_train_valid_test(args)
