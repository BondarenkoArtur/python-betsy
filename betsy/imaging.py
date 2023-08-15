#
# Image processing pipeline
#
# Copyright (c) 2016 Peter McCormick.
#

import numpy as np

# Deprecated
class ImageProcessor(object):
    IDENTITY_T = np.array([
        [ 1.0, 0.0, 0.0 ],
        [ 0.0, 1.0, 0.0 ],
        [ 0.0, 0.0, 1.0 ],
    ])

    # 12-bit full scale value
    PWM_FULL_SCALE = 0x0FFF

    def __init__(self, postscaler=1.0, gamma=2.4, transform=IDENTITY_T):
        self.postscaler = postscaler
        self.gamma = gamma
        self.transform = transform
        self.processed = None

    def process(self, img):
        if img.mode != 'RGB':
            img = img.convert('RGB')

        arr = np.asarray(img, dtype=np.uint8)

        # F: Range into [0, 1]
        postF = arr / 255.0

        # G: Apply gamma exponentiation
        postG = postF ** self.gamma

        # M: Apply channel transformation
        postM = postG.dot(self.transform)

        # P: Apply global post-scaler
        postM *= self.postscaler

        # C: Clamp to keep inside of [0, 1] range
        postC = np.clip(postM, 0.0, 1.0)

        # R: Range from [0, 1] into PWM full scale value
        postR = postC * self.PWM_FULL_SCALE

        return postR

    @staticmethod
    def array2bin(arr):
        return arr.astype(dtype=np.uint16).flatten('C').newbyteorder('B').tostring()

    @staticmethod
    def croparray(arr, xstart, ystart, xend, yend):
        return arr[ystart:yend, xstart:xend]

    def process_and_crop(self, image, cropmap):
        arr = self.process(image)

        for key, cropbox in cropmap.items():
            #(xstart, ystart, xend, yend) = cropbox
            yield key, self.array2bin(self.croparray(arr, *cropbox))
