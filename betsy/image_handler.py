import json
from itertools import product
from betsy.protocol import CommandSocket
from PIL import Image, ImageDraw
import datetime
import time

# Opening JSON file
f = open('inventory.json')
inventory = json.load(f)
tile_size = inventory["settings"]["dimensions"]
dims = [len(inventory["mapping"][0]), len(inventory["mapping"])]

sn_to_ip = {}
for x in inventory["inventory"]:
    sn_to_ip[x["serial_number"]] = x["ipv6_link_local"]

netInt = "enp1s0"


# Tile images returns a 2d array of an input image split into tiles of given size.
# crop-false will scale, crop-true will crop.
def tile_img(img, tilesize=18, matrix_dims=None, crop=False):
    if matrix_dims is None:
        matrix_dims = [9, 6]
    if crop:  # Crop/Scale image to matrix size before anything else:
        img = img.crop((0, 0, tilesize * matrix_dims[0], tilesize * matrix_dims[1]))
    else:
        img = img.resize((tilesize * matrix_dims[0], tilesize * matrix_dims[1]))

    w, h = img.size
    imgs = []
    grid = product(range(0, h - h % tilesize, tilesize), range(0, w - w % tilesize, tilesize))
    for i, j in grid:
        idx_i = int(i / tilesize)
        idx_j = int(j / tilesize)

        box = (j, i, j + tilesize, i + tilesize)
        if len(imgs) < idx_i + 1:
            imgs.append([])
        if len(imgs[idx_i]) < idx_j + 1:
            imgs[idx_i].append([])
        imgs[idx_i][idx_j] = img.crop(box)
    return imgs


# Returns a tile-sized image of the serial #
def serial_img(sn, i=255, j=0):
    image1 = Image.new("RGB", tile_size, (0, 0, 0))
    draw = ImageDraw.Draw(image1)
    draw.text((2, 6), sn, fill=(i, j, 0), align="center")
    return image1


# This sends the image to a given panel.
def send_raw_img(csock, img, destaddr):
    # PROTOCOL.md:
    # ... each consisting of little endian 16-bit per pixel-channel values (48-bit per pixel) arranged left to right, top to bottom.
    # Each buffer is thus 18*18*3*2 or 1944 bytes in size.
    # The high order 4 bits of each 16-bit channel value are ignored.

    img_byte_arr = img.tobytes("raw", "RGB")

    # Here we pad 8bit RGB to 16 bit; note we're losing the top half of the byte so we can't drive full brightness:
    img2 = [0] * 1944
    for x in range(972):
        img2[x * 2] = img_byte_arr[x]

    csock.dpc_data(destaddr, 1, bytes(img2))
    # Finally upload the frame buffer to LEDs:
    csock.dpc_upload(destaddr, 1)


# Simple function to send the Serial number to each panel:
def send_sn_image(inv=inventory):
    csock = CommandSocket(netInt)
    # Note -- This is a little silly. Should probably just use `for i in inv["inventory"]` and ignore the mapping.
    # But this allows us to do the fun gradient.
    for i in range(len(inv["mapping"])):
        for j in range(len(inv["mapping"][i])):
            sn = inv["mapping"][i][j]
            img = serial_img("%d" % sn, 255 - i * 30, 255 - j * 30)
            destaddr = csock.get_ipv6_addr_info(sn_to_ip[sn])

            send_raw_img(csock, img, destaddr)


# Sends an image array
def send_images(imgs, inv=inventory):
    csock = CommandSocket(netInt)
    for i in range(len(inv["mapping"])):
        for j in range(len(inv["mapping"][i])):
            sn = inv["mapping"][i][j]
            img = imgs[i][j]

            destaddr = csock.get_ipv6_addr_info(sn_to_ip[sn])
            send_raw_img(csock, img, destaddr)


# Simple function to send the Serial number to each panel:
def send_reset(inv=inventory):
    csock = CommandSocket(netInt)
    for i in range(len(inv["mapping"])):
        for j in range(len(inv["mapping"][i])):
            sn = inv["mapping"][i][j]
            destaddr = csock.get_ipv6_addr_info(sn_to_ip[sn])
            csock.send_commands("reset firmware", destaddr)


def handle_gif(imageObject, duration=5):
    # TODO: Duration is time to play each gif in seconds, rather than loops
    timetot = 0
    while timetot < duration:
        # Display individual frames from the loaded animated GIF file
        for frame in range(0, imageObject.n_frames):
            start_time = datetime.datetime.now()
            imageObject.seek(frame)
            sleep = imageObject.info['duration'] / 1000
            sleep = sleep if sleep > 0 else 0.16
            new_im = Image.new("RGB", imageObject.size)
            new_im.paste(imageObject)
            hl = tile_img(new_im, 18, crop=False)  # False = scale.
            send_images(hl)
            timetot += sleep
            end_time = datetime.datetime.now()
            diff = end_time - start_time
            actual_sleep = sleep - diff.total_seconds()
            if actual_sleep > 0:
                time.sleep(actual_sleep)


def get_image_object(img_path: str) -> Image.Image:
    return Image.open(img_path)


def handle_image(imageObject, displaytime=5):
    # Potentially uncessary
    new_im = Image.new("RGB", imageObject.size)
    new_im.paste(imageObject)
    # Potentially uncessary

    hl = tile_img(new_im, 18, crop=False)  # False = scale.
    send_images(hl)
    time.sleep(displaytime)


### Use to reset on bootup; call just once:
print("Sending Reset")
send_reset()
# time.sleep(3)

# Call this to call the SNs to the screen and ensure they're in the right order
print("Sending Serial Numbers")
send_sn_image()
