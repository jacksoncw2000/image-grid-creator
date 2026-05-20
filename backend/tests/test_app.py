import io
import tempfile
import unittest

from PIL import Image

from app import create_app
from image_grid import HEIF_SUPPORT_ENABLED


class AppTests(unittest.TestCase):
    def setUp(self):
        self.output_directory = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "OUTPUT_FOLDER": self.output_directory.name,
                "MAX_CONTENT_LENGTH": 1024 * 1024,
                "MAX_OUTPUT_PIXELS": 10_000_000,
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.output_directory.cleanup()

    def test_create_grid_returns_png(self):
        response = self.client.post(
            "/api/create-grid",
            data={
                "files[]": [
                    (_png_stream((210, 70, 80)), "first.png"),
                    (_png_stream((60, 160, 140)), "second.png"),
                ],
                "individualImageSize": "50",
                "randomizedOrder": "false",
                "printerPaperFormat": "false",
                "stretchToSquare": "true",
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/png")
        self.assertIn("image_grid.png", response.headers["Content-Disposition"])
        response.close()

    @unittest.skipUnless(HEIF_SUPPORT_ENABLED, "pillow-heif is not installed")
    def test_create_grid_accepts_heic_upload(self):
        response = self.client.post(
            "/api/create-grid",
            data={
                "files[]": [(_heic_stream((80, 130, 210)), "first.HEIC")],
                "individualImageSize": "50",
                "randomizedOrder": "false",
                "printerPaperFormat": "false",
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/png")
        response.close()

    def test_create_grid_accepts_collage_layout(self):
        response = self.client.post(
            "/api/create-grid",
            data={
                "files[]": [(_png_stream((30, 90, 150)), "wide.png")],
                "individualImageSize": "50",
                "randomizedOrder": "false",
                "collageLayout": "true",
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/png")

        with Image.open(io.BytesIO(response.get_data())) as generated:
            self.assertEqual(generated.mode, "RGBA")
            self.assertEqual(generated.size, (50, 50))

        response.close()

    def test_unsupported_file_type_returns_400(self):
        response = self.client.post(
            "/api/create-grid",
            data={"files[]": [(io.BytesIO(b"not an image"), "notes.txt")]},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported file type", response.get_json()["error"]["message"])

    def test_too_large_output_returns_400(self):
        app = create_app(
            {
                "TESTING": True,
                "OUTPUT_FOLDER": self.output_directory.name,
                "MAX_CONTENT_LENGTH": 1024 * 1024,
                "MAX_OUTPUT_PIXELS": 100,
            }
        )

        response = app.test_client().post(
            "/api/create-grid",
            data={
                "files[]": [(_png_stream((20, 40, 80)), "first.png")],
                "individualImageSize": "50",
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Requested grid is too large", response.get_json()["error"]["message"])

    def test_too_large_upload_returns_413(self):
        app = create_app(
            {
                "TESTING": True,
                "OUTPUT_FOLDER": self.output_directory.name,
                "MAX_CONTENT_LENGTH": 128,
                "MAX_OUTPUT_PIXELS": 10_000_000,
            }
        )

        response = app.test_client().post(
            "/api/create-grid",
            data={"files[]": [(io.BytesIO(b"x" * 1024), "image.png")]},
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 413)
        self.assertIn("Upload is too large", response.get_json()["error"]["message"])


def _png_stream(color):
    stream = io.BytesIO()
    Image.new("RGB", (10, 10), color).save(stream, format="PNG")
    stream.seek(0)
    return stream


def _heic_stream(color):
    stream = io.BytesIO()
    Image.new("RGB", (10, 10), color).save(stream, format="HEIF")
    stream.seek(0)
    return stream


if __name__ == "__main__":
    unittest.main()
