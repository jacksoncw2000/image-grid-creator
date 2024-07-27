import os
import datetime
import math
import random
from tqdm import tqdm
from PIL import Image, ExifTags


def grid_images(input_folder, base_directory_name, outputs_directory, individual_image_size=1000, randomized_order=True, printer_paper_format=False):

    current_date_time = datetime.datetime.now()
    current_date_time = current_date_time.strftime('%Y%m%d_%H%M%S')

    print(f'\n[INFO] Attempting to grid images.\n')

    image_files = os.listdir(input_folder)

    if '.DS_Store' in image_files:
        image_files.remove('.DS_Store')

    images_array = []

    for image_file in image_files:
        images_array.append(image_file)

    if randomized_order:  # Shuffle the images_array if randomized_order is True
        random.shuffle(images_array)

    number_of_images_uploaded = len(images_array)

    if printer_paper_format:
        aspect_ratio = 8.5 / 11.0  # Aspect ratio of standard printer paper
        grid_width = int(math.sqrt(number_of_images_uploaded * aspect_ratio) * individual_image_size)
        grid_height = int(math.sqrt(number_of_images_uploaded / aspect_ratio) * individual_image_size)
    else:
        grid_width = int(math.sqrt(number_of_images_uploaded) * individual_image_size)
        grid_height = int(math.sqrt(number_of_images_uploaded) * individual_image_size)

    grid = Image.new("RGB", (grid_width, grid_height), (255, 255, 255))

    thumbnail_width = int(grid_width / math.sqrt(len(images_array)))
    thumbnail_height = int(grid_height / math.sqrt(len(images_array)))

    for i, image in tqdm(enumerate(images_array), total=len(images_array), desc="Processing images"):

        image = Image.open(f'{input_folder}/{image}')

        exif_data = image._getexif()
        if exif_data is not None:
            exif = {ExifTags.TAGS[k]: v for k, v in image._getexif().items() if k in ExifTags.TAGS}

        image = image.resize((thumbnail_width, thumbnail_height))

        if exif_data is not None:
            if 'Orientation' in exif:
                if exif['Orientation'] == 3:
                    image = image.rotate(180)
                elif exif['Orientation'] == 6:
                    image = image.rotate(270)
                elif exif['Orientation'] == 8:
                    image = image.rotate(90)

        x = i % int(math.sqrt(len(images_array))) * thumbnail_width
        y = i // int(math.sqrt(len(images_array))) * thumbnail_height

        grid.paste(image, (x, y))

    file_output_path = os.path.join(outputs_directory, f"{current_date_time}_{base_directory_name}.png")
    grid.save(file_output_path)

    print("\n[INFO] Image grid complete.\n")

    return file_output_path