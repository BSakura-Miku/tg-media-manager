from __future__ import annotations

import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from backend.app import main


@unittest.skipIf(main.Image is None, "Pillow is not installed")
class FaceThumbnailTests(unittest.TestCase):
    def test_parse_face_bbox_rejects_invalid_values(self) -> None:
        self.assertIsNone(main.parse_face_bbox(""))
        self.assertIsNone(main.parse_face_bbox("[10, 10, 5, 20]"))
        self.assertIsNone(main.parse_face_bbox("[1, 2, 3]"))
        self.assertEqual(main.parse_face_bbox("[1, 2, 11, 22]"), (1.0, 2.0, 11.0, 22.0))

    def test_render_face_thumbnail_crops_to_the_selected_face(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            source = Path(tempdir) / "frame.jpg"
            image = main.Image.new("RGB", (400, 200), "black")
            for x in range(20, 121):
                for y in range(40, 161):
                    image.putpixel((x, y), (230, 20, 20))
            for x in range(280, 381):
                for y in range(40, 161):
                    image.putpixel((x, y), (20, 20, 230))
            image.save(source, "JPEG", quality=95)

            payload = main.render_face_thumbnail(source, "[20, 40, 120, 160]")

            self.assertIsNotNone(payload)
            with main.Image.open(BytesIO(payload)) as cropped:
                self.assertEqual(cropped.width, cropped.height)
                pixels = list(cropped.convert("RGB").getdata())
                red = sum(pixel[0] for pixel in pixels)
                blue = sum(pixel[2] for pixel in pixels)
                self.assertGreater(red, blue * 3)

    def test_render_face_thumbnail_pads_edge_faces_to_a_square(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            source = Path(tempdir) / "edge.jpg"
            main.Image.new("RGB", (200, 100), "white").save(source, "JPEG")

            payload = main.render_face_thumbnail(source, "[60, -20, 120, 35]")

            self.assertIsNotNone(payload)
            with main.Image.open(BytesIO(payload)) as cropped:
                self.assertEqual(cropped.width, cropped.height)


if __name__ == "__main__":
    unittest.main()
