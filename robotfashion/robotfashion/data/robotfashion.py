import os
import json

import numpy as np
import torch as t

from .util import has_correct_folder_structure, maybe_download_and_unzip_data

from torchvision.datasets import VisionDataset
from PIL import Image
from enum import Enum

import xml.etree.ElementTree as ET


class DF2(Enum):
    short_sleeve_top = 1
    long_sleeve_top = 2
    short_sleeve_outwear = 3
    long_sleeve_outwear = 4
    vest = 5
    sling = 6
    shorts = 7
    trousers = 8
    skirt = 9
    short_sleeve_dress = 10
    long_sleeve_dress = 11
    vest_dress = 12
    sling_dress = 13


df2_enum_to_name = {
    DF2.short_sleeve_top: "short_sleeve_top",
    DF2.long_sleeve_top: "long_sleeve_top",
    DF2.short_sleeve_outwear: "short_sleeve_outwear",
    DF2.long_sleeve_outwear: "long_sleeve_outwear",
    DF2.vest: "vest",
    DF2.sling: "sling",
    DF2.shorts: "shorts",
    DF2.trousers: "trousers",
    DF2.skirt: "skirt",
    DF2.short_sleeve_dress: "short_sleeve_dress",
    DF2.long_sleeve_dress: "long_sleeve_dress",
    DF2.vest_dress: "vest_dress",
    DF2.sling_dress: "sling_dress",
}

name_to_df2_enum = {
    "short_sleeve_top": DF2.short_sleeve_top,
    "long_sleeve_top": DF2.long_sleeve_top,
    "short_sleeve_outwear": DF2.short_sleeve_outwear,
    "long_sleeve_outwear": DF2.long_sleeve_outwear,
    "vest": DF2.vest,
    "sling": DF2.sling,
    "shorts": DF2.shorts,
    "trousers": DF2.trousers,
    "skirt": DF2.skirt,
    "short_sleeve_dress": DF2.short_sleeve_dress,
    "long_sleeve_dres": DF2.long_sleeve_dress,
    "vest_dress": DF2.vest_dress,
    "sling_dress": DF2.sling_dress,
}


def get_class_from_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    for child in root:
        if child.tag == "object":
            clazz = child[0]

            return name_to_df2_enum[clazz.text].value

    raise ValueError("no name in xml")


def get_bbox_from_xml(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    for child in root:
        if child.tag == "object":
            for grandchild in child:
                if grandchild.tag == "bndbox":
                    return extract_bb(grandchild)

    raise ValueError("no bounding box in xml")


def extract_bb(xml_obj):
    xmin = -1
    xmax = -1
    ymin = -1
    ymax = -1

    for child in xml_obj:
        if child.tag == "xmin":
            xmin = int(child.text)
        if child.tag == "xmax":
            xmax = int(child.text)
        if child.tag == "ymin":
            ymin = int(child.text)
        if child.tag == "ymax":
            ymax = int(child.text)

    if xmin < 0 or xmax < 0 or ymin < 0 or ymax < 0:
        raise ValueError("no xmin,xmax,ymin,ymax in xml")

    return [xmin, xmax, ymin, ymax]


class RobotFashion(VisionDataset):
    train_mode = "train"
    val_mode = "val"
    test_mode = "test"
    modes = [train_mode, val_mode, test_mode]

    def __init__(
        self,
        working_path: str,
        mode: str,
        download_if_missing: bool = False,
        subset_ratio=1,
        transform=None,
    ):
        super().__init__(working_path, transform=transform, target_transform=None)

        if not has_correct_folder_structure(
            self._get_root_data_folder(), self.get_folders(), self.get_dataset_name()
        ):
            if not download_if_missing:
                raise ValueError(
                    f"cannot find (valid) {self.get_dataset_name()} data."
                    + " Set download_if_missing=True to download dataset"
                )

            maybe_download_and_unzip_data(
                self._get_root_data_folder(), self.get_download_links()
            )

            if not has_correct_folder_structure(
                self._get_root_data_folder(),
                self.get_folders(),
                self.get_dataset_name(),
            ):
                raise Exception("Downloading and/or unzipping data failed")

        if mode not in RobotFashion.modes:
            raise ValueError(f"mode {mode} should be one of {RobotFashion.modes}")

        if subset_ratio <= 0 or subset_ratio > 1:
            raise ValueError(f"subset ratio {subset_ratio} needs to be in (0, 1]")
        else:
            self.subset_ratio = subset_ratio

        self.mode = mode

        if mode == RobotFashion.train_mode:
            self.image_paths, self.label_paths = self.load_train_data()
        elif mode == RobotFashion.val_mode:
            self.image_paths, self.label_paths = self.load_val_data()
        else:
            self.image_paths, self.label_paths = self.load_test_data()

    def _get_root_data_folder(self):
        return os.path.join(self.root, self.get_data_folder_name())

    def load_train_data(self):
        return self.load_data(os.path.join(self._get_root_data_folder(), "train"))

    def load_val_data(self):
        return self.load_data(os.path.join(self._get_root_data_folder(), "validation"))

    def load_test_data(self):
        # return self.load_data(
        #     os.path.join(get_root_data_folder(self.root), "test")
        # )
        raise NotImplementedError("labels of test data are not published")

    def __getitem__(self, index):
        image = self.load_image(self.image_paths[index])
        label = self.load_label(self.label_paths[index])

        if self.transform is not None:
            image = self.transform(image)

        return image, label

    def __len__(self):
        n = len(self.image_paths)

        return int(self.subset_ratio * n)

    @staticmethod
    def load_data(data_dir):
        image_dir = os.path.join(data_dir, "images")
        annos_dir = os.path.join(data_dir, "annotations")

        image_paths = [
            os.path.join(image_dir, f)
            for f in sorted(os.listdir(image_dir))
            if os.path.isfile(os.path.join(image_dir, f))
        ]
        label_paths = [
            os.path.join(annos_dir, f)
            for f in sorted(os.listdir(annos_dir))
            if os.path.isfile(os.path.join(annos_dir, f))
        ]

        if len(image_paths) != len(label_paths):
            raise ValueError("length of images and labels doesn't match")

        return image_paths, label_paths

    @staticmethod
    def load_image(image_path):
        img = Image.open(image_path)

        return img

    @staticmethod
    def load_label(label_path):
        # During training, the model expects both the input tensors, as well as a targets (list of dictionary),
        # containing:
        #     - boxes (FloatTensor[N, 4]): the ground-truth boxes in [x1, y1, x2, y2] format, with values
        #       between 0 and H and 0 and W
        #     - labels (Int64Tensor[N]): the class label for each ground-truth box
        boxes = np.zeros((1, 4))
        labels = np.zeros((1,))

        boxes[0, :] = get_bbox_from_xml(label_path)
        labels[0] = get_class_from_xml(label_path)

        return {"boxes": t.tensor(boxes).float(), "labels": t.tensor(labels).long()}

    @classmethod
    def get_data_folder_name(cls):
        return f"{cls.get_dataset_name()}_data_folder"

    @staticmethod
    def get_dataset_name():
        return "robotfashion"

    @staticmethod
    def get_download_links():
        return [
            # order:
            # 1. google drive id,
            # 2. file name,
            # 3. sha256 hash of zipfile,
            # 4. data length of zipfile
            (
                "1ezwR5_7OHhqjMR2D9ZMZqpq8u8xQ2MoG",
                "robotfashion_dataset.zip",
                "5a66924dbe44eed9bc0cdf52a206470db2fd9421a5745ab17b18588952c14ba4",
                1050691281,
            )
        ]

    @staticmethod
    def get_folders():
        return [
            # order:
            # 1. folder name
            # 2. sha256 hash of all file and subfolder names
            #    concatenated to a string (without spaces as separation)
            (
                "train",
                "369ba5f28b246d2903b8f686b18d4b89b668fa484c9baef55c1c8bc5b6f2a45e",
            ),
            ("val", "369ba5f28b246d2903b8f686b18d4b89b668fa484c9baef55c1c8bc5b6f2a45e"),
            (
                "test",
                "369ba5f28b246d2903b8f686b18d4b89b668fa484c9baef55c1c8bc5b6f2a45e",
            ),
        ]
