#!/bin/env python3

import os
import random
import time

from betsy.image_handler import get_image_object, handle_gif, handle_image, prepare_image, \
    send_reset

GIF_ONLY = True
SUBDIR = 'cool/'
PATH_PREFIX = 'image/' + SUBDIR


def prepare_images():
    """
    Function for going once through all the files to generate scaled tiles for each frame.
    """
    for file in os.listdir(PATH_PREFIX):
        if not file.__contains__("DS_Store"):
            print("Processing image:", PATH_PREFIX + file)
            prepare_image(PATH_PREFIX + file)


def loop_with_images():
    """
    Function with infinite loop for showing gifs and images.
    Takes the folder PATH_PREFIX, shuffles order of images and showing them on screen.
    GIF_ONLY constant is for showing or not showing static images.
    """
    while True:
        send_reset()
        files = os.listdir(PATH_PREFIX)
        random.shuffle(files)
        for file in files:
            if not file.__contains__("DS_Store"):  # Ignoring thumbnails
                image_object = get_image_object(img_path=PATH_PREFIX + file)
                if getattr(image_object, "is_animated", True):
                    handle_gif(image_object)
                else:
                    if not GIF_ONLY:
                        handle_image(PATH_PREFIX + file, 5)
                        time.sleep(0.001)


if __name__ == '__main__':
    prepare_images()
    loop_with_images()
