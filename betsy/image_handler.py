import datetime
import json
import time

from itertools import product
from PIL import Image, ImageDraw

from betsy.protocol import CommandSocket

ENABLED_OUTPUT = True

# Opening config JSON file
INVENTORY = json.load(open('inventory.json', encoding="utf8"))
TILE_SIZE = INVENTORY["settings"]["dimensions"]

SN_TO_IP = {}
for inv in INVENTORY["inventory"]:
    SN_TO_IP[inv["serial_number"]] = inv["ipv6_link_local"]

if ENABLED_OUTPUT:
    SOCKET = CommandSocket("enp1s0")

LOADED_IMAGES = {}
SLEEP_DURATION = {}


def tile_img(img, matrix_dims=None, crop=False):
    """
    Tile images returns a 2d array of an input image split into tiles of given size.
    crop-false will scale, crop-true will crop.
    """
    if matrix_dims is None:
        matrix_dims = [9, 6]
    if crop:  # Crop/Scale image to matrix size before anything else:
        img = img.crop((0, 0, TILE_SIZE[0] * matrix_dims[0], TILE_SIZE[1] * matrix_dims[1]))
    else:
        img = img.resize((TILE_SIZE[0] * matrix_dims[0], TILE_SIZE[1] * matrix_dims[1]))

    width, height = img.size
    tiles = []
    grid = product(range(0, height - height % TILE_SIZE[1], TILE_SIZE[1]),
                   range(0, width - width % TILE_SIZE[0], TILE_SIZE[0]))
    for i, j in grid:
        idx_i = int(i / TILE_SIZE[0])
        idx_j = int(j / TILE_SIZE[1])

        box = (j, i, j + TILE_SIZE[1], i + TILE_SIZE[0])
        if len(tiles) < idx_i + 1:
            tiles.append([])
        if len(tiles[idx_i]) < idx_j + 1:
            tiles[idx_i].append([])
        tiles[idx_i][idx_j] = img.crop(box)
    return tiles


def serial_img(serial_number, i=255, j=0):
    """
    Returns a tile-sized image of the serial
    """
    image1 = Image.new("RGB", TILE_SIZE, (0, 0, 0))
    draw = ImageDraw.Draw(image1)
    draw.text((2, 6), serial_number, fill=(i, j, 0), align="center")
    return image1


def send_raw_tile(img, destaddr):
    """
    This sends the image to a given panel.
    """
    # PROTOCOL.md:
    # ... each consisting of little endian 16-bit per pixel-channel values (48-bit per pixel)
    # arranged left to right, top to bottom.
    # Each buffer is thus 18*18*3*2 or 1944 bytes in size.
    # The high order 4 bits of each 16-bit channel value are ignored.

    img_byte_arr = img.tobytes("raw", "RGB")

    # Here we pad 8bit RGB to 16 bit;
    # note we're losing the top half of the byte, so we can't drive full brightness:
    img2 = [0] * 1944
    for i in range(972):
        img2[i * 2] = img_byte_arr[i]

    SOCKET.dpc_data(destaddr, 1, bytes(img2))
    # Finally upload the frame buffer to LEDs:
    SOCKET.dpc_upload(destaddr, 1)


def send_sn_image():
    """
    Simple function to send the Serial number to each panel
    """
    if not ENABLED_OUTPUT:
        return
    # Note -- This is a little silly.
    # Should probably just use `for i in inv["inventory"]` and ignore the mapping.
    # But this allows us to do the fun gradient.
    for i in range(len(INVENTORY["mapping"])):
        for j in range(len(INVENTORY["mapping"][i])):
            serial_number = INVENTORY["mapping"][i][j]
            img = serial_img(f"{serial_number:d}", 255 - i * 30, 255 - j * 30)
            destination_address = SOCKET.get_ipv6_addr_info(SN_TO_IP[serial_number])
            send_raw_tile(img, destination_address)


def send_images(tiles):
    """
    Sends an image array
    """
    if not ENABLED_OUTPUT:
        return
    for i in range(len(INVENTORY["mapping"])):
        for j in range(len(INVENTORY["mapping"][i])):
            serial_number = INVENTORY["mapping"][i][j]
            tile = tiles[i][j]
            destination_address = SOCKET.get_ipv6_addr_info(SN_TO_IP[serial_number])
            send_raw_tile(tile, destination_address)


def send_reset():
    """
    Simple function to send the Serial number to each panel:
    """
    if not ENABLED_OUTPUT:
        return
    for i in range(len(INVENTORY["mapping"])):
        for j in range(len(INVENTORY["mapping"][i])):
            serial_number = INVENTORY["mapping"][i][j]
            destination_address = SOCKET.get_ipv6_addr_info(SN_TO_IP[serial_number])
            SOCKET.send_commands("reset firmware", destination_address)


def handle_gif(image_object, duration=5):
    """
    Displays gif on the screen.
    Duration is minimum time gif is on the screen, maximum is limited by actual gif duration.
    """
    time_total = 0
    if image_object.filename not in LOADED_IMAGES:
        prepare_image(image_object.filename)
    image = LOADED_IMAGES[image_object.filename]
    sleeps = SLEEP_DURATION[image_object.filename]
    while time_total <= duration:
        # Display individual frames from the loaded animated GIF file
        for frame_number in range(0, len(image)):
            start_time = datetime.datetime.now()
            gif_frame = image[frame_number]
            sleep = sleeps[frame_number]
            send_images(gif_frame)
            time_total += sleep
            end_time = datetime.datetime.now()
            diff = end_time - start_time
            actual_sleep = sleep - diff.total_seconds()
            if ENABLED_OUTPUT and actual_sleep > 0:
                time.sleep(actual_sleep)


def get_image_object(img_path: str) -> Image.Image:
    return Image.open(img_path)


def prepare_image(img_path: str):
    """
    This goes through each frame in gif, scales and places into RAM.
    """
    LOADED_IMAGES[img_path] = []
    SLEEP_DURATION[img_path] = []
    image_object = get_image_object(img_path)
    if getattr(image_object, "is_animated", True):
        for frame_number in range(0, image_object.n_frames):
            image_object.seek(frame_number)
            sleep = image_object.info['duration'] / 1000
            sleep = sleep if sleep > 0 else 0.16
            SLEEP_DURATION[img_path].append(sleep)
            new_im = Image.new("RGB", image_object.size)
            new_im.paste(image_object)
            gif_frame = tile_img(new_im)
            LOADED_IMAGES[img_path].append(gif_frame)


def handle_image(image_object, display_time=5):
    """
    Displays static image on the screen
    """
    # Potentially unnecessary
    new_im = Image.new("RGB", image_object.size)
    new_im.paste(image_object)
    # Potentially unnecessary

    image_frame = tile_img(new_im)
    send_images(image_frame)
    time.sleep(display_time)


# Use to reset on boot-up; call just once:
print("Sending Reset")
send_reset()

# Call this to call the SNs to the screen and ensure they're in the right order
print("Sending Serial Numbers")
send_sn_image()
