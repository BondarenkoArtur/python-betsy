#!/bin/env python3

import os
import random
import time
from betsy.image_handler import send_reset, handle_gif, get_image_object

# Here, draw a picture!
# img = Image.open("nyan2.jpg")
# hl = tile_img(img, 18, crop=False) # False = scale.
# send_images(hl)

# while 1:
#   imageObject = Image.open('rainbow.gif')
#   handle_gif(imageObject)

# Comment out as you want to configure it.
# subdir = 'test/'
subdir = 'cool/'
# subdir = 'meme/'
pathPrefix = 'image/' + subdir
while 1:
    send_reset()
    files = os.listdir(pathPrefix)
    random.shuffle(files)
    for file in files:
        if not file.__contains__("DS_Store"):
            imageObject = get_image_object(img_path=pathPrefix + file)
            if getattr(imageObject, "is_animated", True):
                handle_gif(imageObject)
            else:
                # Comment out for GIF ONLY MODE.
                # handle_image(imgPath, 5)
                time.sleep(0.001)
