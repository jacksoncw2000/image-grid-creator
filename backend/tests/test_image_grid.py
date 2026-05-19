import io
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from image_grid import (
    GridOptions,
    HEIF_SUPPORT_ENABLED,
    ImageInput,
    PRINTER_PAPER_ASPECT_RATIO,
    choose_layout,
    generate_image_grid,
)


class ImageGridTests(unittest.TestCase):
    def test_choose_layout_for_square_grid(self):
        layout = choose_layout(144)

        self.assertEqual((layout.columns, layout.rows), (12, 12))

    def test_choose_layout_for_printer_shape(self):
        layout = choose_layout(144, PRINTER_PAPER_ASPECT_RATIO)

        self.assertEqual((layout.columns, layout.rows), (11, 14))

    def test_generate_image_grid_from_streams(self):
        inputs = [
            ImageInput(name=f"image-{index}.png", stream=_png_stream((index * 30, 90, 180)))
            for index in range(5)
        ]

        with tempfile.TemporaryDirectory() as directory:
            result = generate_image_grid(
                image_inputs=inputs,
                output_directory=directory,
                options=GridOptions(
                    individual_image_size=50,
                    randomized_order=False,
                ),
            )

            self.assertTrue(result.path.exists())
            self.assertEqual((result.layout.columns, result.layout.rows), (3, 2))

            with Image.open(result.path) as generated:
                self.assertEqual(generated.size, (150, 100))

    def test_preserves_aspect_ratio_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            result = generate_image_grid(
                image_inputs=[ImageInput(name="wide.png", stream=_png_stream((20, 80, 160)))],
                output_directory=directory,
                options=GridOptions(
                    individual_image_size=50,
                    randomized_order=False,
                ),
            )

            with Image.open(result.path) as generated:
                self.assertEqual(generated.getpixel((0, 0)), (255, 255, 255))
                self.assertEqual(generated.getpixel((25, 25)), (20, 80, 160))

    def test_can_stretch_images_to_square_cells(self):
        with tempfile.TemporaryDirectory() as directory:
            result = generate_image_grid(
                image_inputs=[ImageInput(name="wide.png", stream=_png_stream((20, 80, 160)))],
                output_directory=directory,
                options=GridOptions(
                    individual_image_size=50,
                    randomized_order=False,
                    stretch_to_square=True,
                ),
            )

            with Image.open(result.path) as generated:
                self.assertEqual(generated.size, (50, 50))
                self.assertEqual(generated.getpixel((0, 0)), (20, 80, 160))
                self.assertEqual(generated.getpixel((49, 49)), (20, 80, 160))

    @unittest.skipUnless(HEIF_SUPPORT_ENABLED, "pillow-heif is not installed")
    def test_generate_image_grid_from_heic_without_modifying_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source_path = Path(directory) / "source.HEIC"
            _save_heic(source_path, (90, 140, 210))
            original_bytes = source_path.read_bytes()

            with source_path.open("rb") as source_stream:
                result = generate_image_grid(
                    image_inputs=[ImageInput(name=source_path.name, stream=source_stream)],
                    output_directory=directory,
                    options=GridOptions(
                        individual_image_size=50,
                        randomized_order=False,
                    ),
                )

            self.assertTrue(result.path.exists())
            self.assertEqual(source_path.read_bytes(), original_bytes)

            with Image.open(result.path) as generated:
                self.assertEqual(generated.size, (50, 50))


def _png_stream(color):
    stream = io.BytesIO()
    Image.new("RGB", (18, 12), color).save(stream, format="PNG")
    stream.seek(0)
    return stream


def _save_heic(path, color):
    Image.new("RGB", (24, 18), color).save(path, format="HEIF")


if __name__ == "__main__":
    unittest.main()
