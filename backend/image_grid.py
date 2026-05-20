from __future__ import annotations

import datetime as dt
import math
import random
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterable, Iterator, List, Optional, Sequence, Tuple, TypeVar, Union
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError

try:
    from pillow_heif import register_heif_opener
except ImportError:  # pragma: no cover - exercised only when optional dependency is absent.
    HEIF_SUPPORT_ENABLED = False
else:
    register_heif_opener()
    HEIF_SUPPORT_ENABLED = True


SUPPORTED_EXTENSIONS = frozenset(
    {"bmp", "gif", "heic", "heif", "jpeg", "jpg", "png", "tif", "tiff", "webp"}
)
HEIF_EXTENSIONS = frozenset({"heic", "heif"})

DEFAULT_BACKGROUND_COLOR = (255, 255, 255)
DEFAULT_MAX_OUTPUT_PIXELS = 300_000_000
PRINTER_PAPER_ASPECT_RATIO = 8.5 / 11.0

try:
    RESAMPLE_FILTER = Image.Resampling.LANCZOS
except AttributeError:  # pragma: no cover - compatibility with old Pillow releases.
    RESAMPLE_FILTER = Image.LANCZOS


class ImageGridError(Exception):
    """Base exception for user-facing grid generation errors."""


class InvalidImageGridRequest(ImageGridError):
    """Raised when a request cannot produce a valid grid."""


class InvalidImageFile(ImageGridError):
    """Raised when Pillow cannot read one of the uploaded images."""


@dataclass(frozen=True)
class GridOptions:
    individual_image_size: int = 1000
    randomized_order: bool = True
    printer_paper_format: bool = False
    stretch_to_square: bool = False
    collage_layout: bool = False
    background_color: Tuple[int, int, int] = DEFAULT_BACKGROUND_COLOR
    max_output_pixels: int = DEFAULT_MAX_OUTPUT_PIXELS
    random_seed: Optional[int] = None


@dataclass(frozen=True)
class GridLayout:
    columns: int
    rows: int
    cell_size: int
    width_pixels: Optional[int] = None
    height_pixels: Optional[int] = None

    @property
    def width(self) -> int:
        return self.width_pixels or self.columns * self.cell_size

    @property
    def height(self) -> int:
        return self.height_pixels or self.rows * self.cell_size

    @property
    def pixel_count(self) -> int:
        return self.width * self.height


@dataclass(frozen=True)
class ImageInput:
    name: str
    stream: BinaryIO


@dataclass(frozen=True)
class GeneratedGrid:
    path: Path
    download_name: str
    layout: GridLayout
    image_count: int


@dataclass(frozen=True)
class CollagePlacement:
    index: int
    x: int
    y: int
    width: int
    height: int


T = TypeVar("T")


def is_supported_filename(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in SUPPORTED_EXTENSIONS


def choose_layout(image_count: int, target_aspect_ratio: float = 1.0) -> GridLayout:
    if image_count <= 0:
        raise InvalidImageGridRequest("Select at least one image.")

    best_columns = 1
    best_rows = image_count
    best_score = None

    for columns in range(1, image_count + 1):
        rows = math.ceil(image_count / columns)
        aspect_ratio = columns / rows
        aspect_penalty = abs(math.log(aspect_ratio / target_aspect_ratio))
        empty_cells = (columns * rows) - image_count
        orientation_penalty = _orientation_penalty(columns, rows, target_aspect_ratio)
        balance_penalty = abs(columns - rows)
        score = (
            round(aspect_penalty, 12),
            empty_cells,
            orientation_penalty,
            balance_penalty,
        )

        if best_score is None or score < best_score:
            best_columns = columns
            best_rows = rows
            best_score = score

    return GridLayout(columns=best_columns, rows=best_rows, cell_size=1)


def generate_image_grid(
    image_inputs: Sequence[ImageInput],
    output_directory: Union[Path, str],
    options: Optional[GridOptions] = None,
) -> GeneratedGrid:
    options = options or GridOptions()
    inputs = list(image_inputs)
    _validate_options(options)
    _validate_image_count(len(inputs))
    _order_items(inputs, options)

    if options.collage_layout:
        return _generate_collage_from_inputs(inputs, output_directory, options)

    layout = _layout_for_options(len(inputs), options)
    _validate_output_size(layout, options)

    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    with Image.new("RGB", (layout.width, layout.height), options.background_color) as grid:
        for index, image_input in enumerate(inputs):
            with _open_existing_stream(image_input.stream) as stream:
                tile = _make_tile(
                    stream,
                    image_input.name,
                    layout.cell_size,
                    options.background_color,
                    options.stretch_to_square,
                )

            x = (index % layout.columns) * layout.cell_size
            y = (index // layout.columns) * layout.cell_size
            grid.paste(tile, (x, y))
            tile.close()

        timestamp = dt.datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
        download_name = f"{timestamp}_image_grid.png"
        output_path = output_directory / f"{timestamp}_{uuid4().hex[:8]}_image_grid.png"
        grid.save(output_path, format="PNG")

    return GeneratedGrid(
        path=output_path,
        download_name=download_name,
        layout=layout,
        image_count=len(inputs),
    )


def generate_image_grid_from_paths(
    image_paths: Iterable[Union[Path, str]],
    output_directory: Union[Path, str],
    options: Optional[GridOptions] = None,
) -> GeneratedGrid:
    options = options or GridOptions()
    paths = [Path(path) for path in image_paths]
    _validate_options(options)
    _validate_image_count(len(paths))
    _order_items(paths, options)

    if options.collage_layout:
        return _generate_collage_from_paths(paths, output_directory, options)

    layout = _layout_for_options(len(paths), options)
    _validate_output_size(layout, options)

    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    with Image.new("RGB", (layout.width, layout.height), options.background_color) as grid:
        for index, path in enumerate(paths):
            with path.open("rb") as stream:
                tile = _make_tile(
                    stream,
                    path.name,
                    layout.cell_size,
                    options.background_color,
                    options.stretch_to_square,
                )

            x = (index % layout.columns) * layout.cell_size
            y = (index // layout.columns) * layout.cell_size
            grid.paste(tile, (x, y))
            tile.close()

        timestamp = dt.datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
        download_name = f"{timestamp}_image_grid.png"
        output_path = output_directory / f"{timestamp}_{uuid4().hex[:8]}_image_grid.png"
        grid.save(output_path, format="PNG")

    return GeneratedGrid(
        path=output_path,
        download_name=download_name,
        layout=layout,
        image_count=len(paths),
    )


def _generate_collage_from_inputs(
    inputs: Sequence[ImageInput],
    output_directory: Union[Path, str],
    options: GridOptions,
) -> GeneratedGrid:
    aspect_ratios = []
    for image_input in inputs:
        with _open_existing_stream(image_input.stream) as stream:
            aspect_ratios.append(_image_aspect_ratio(stream, image_input.name))

    layout, placements = _collage_layout(aspect_ratios, options)
    _validate_output_size(layout, options)

    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    with Image.new("RGBA", (layout.width, layout.height), (0, 0, 0, 0)) as canvas:
        for placement in placements:
            image_input = inputs[placement.index]
            with _open_existing_stream(image_input.stream) as stream:
                tile = _make_collage_tile(
                    stream,
                    image_input.name,
                    placement.width,
                    placement.height,
                )

            _paste_image(canvas, tile, (placement.x, placement.y))
            tile.close()

        output_path, download_name = _output_paths(output_directory)
        canvas.save(output_path, format="PNG")

    return GeneratedGrid(
        path=output_path,
        download_name=download_name,
        layout=layout,
        image_count=len(inputs),
    )


def _generate_collage_from_paths(
    paths: Sequence[Path],
    output_directory: Union[Path, str],
    options: GridOptions,
) -> GeneratedGrid:
    aspect_ratios = []
    for path in paths:
        with path.open("rb") as stream:
            aspect_ratios.append(_image_aspect_ratio(stream, path.name))

    layout, placements = _collage_layout(aspect_ratios, options)
    _validate_output_size(layout, options)

    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)

    with Image.new("RGBA", (layout.width, layout.height), (0, 0, 0, 0)) as canvas:
        for placement in placements:
            path = paths[placement.index]
            with path.open("rb") as stream:
                tile = _make_collage_tile(
                    stream,
                    path.name,
                    placement.width,
                    placement.height,
                )

            _paste_image(canvas, tile, (placement.x, placement.y))
            tile.close()

        output_path, download_name = _output_paths(output_directory)
        canvas.save(output_path, format="PNG")

    return GeneratedGrid(
        path=output_path,
        download_name=download_name,
        layout=layout,
        image_count=len(paths),
    )


def _layout_for_options(image_count: int, options: GridOptions) -> GridLayout:
    target_aspect_ratio = PRINTER_PAPER_ASPECT_RATIO if options.printer_paper_format else 1.0
    base_layout = choose_layout(image_count, target_aspect_ratio)
    return GridLayout(
        columns=base_layout.columns,
        rows=base_layout.rows,
        cell_size=options.individual_image_size,
    )


def _collage_layout(
    aspect_ratios: Sequence[float],
    options: GridOptions,
) -> Tuple[GridLayout, List[CollagePlacement]]:
    best_layout = None
    best_placements = None
    best_score = None

    for columns in range(1, len(aspect_ratios) + 1):
        layout, placements, column_heights = _place_collage_columns(
            aspect_ratios,
            columns,
            options.individual_image_size,
        )
        aspect_ratio = layout.width / layout.height
        aspect_penalty = abs(math.log(aspect_ratio))
        ragged_edge = max(column_heights) - min(column_heights)
        score = (
            round(aspect_penalty, 12),
            ragged_edge,
            columns,
        )

        if best_score is None or score < best_score:
            best_layout = layout
            best_placements = placements
            best_score = score

    return best_layout, best_placements


def _place_collage_columns(
    aspect_ratios: Sequence[float],
    columns: int,
    column_width: int,
) -> Tuple[GridLayout, List[CollagePlacement], List[int]]:
    column_heights = [0 for _ in range(columns)]
    placements = []

    for index, aspect_ratio in enumerate(aspect_ratios):
        column = min(range(columns), key=lambda current: column_heights[current])
        height = max(1, round(column_width / aspect_ratio))
        x = column * column_width
        y = column_heights[column]

        placements.append(
            CollagePlacement(
                index=index,
                x=x,
                y=y,
                width=column_width,
                height=height,
            )
        )
        column_heights[column] += height

    width = columns * column_width
    height = max(column_heights)
    layout = GridLayout(
        columns=columns,
        rows=0,
        cell_size=column_width,
        width_pixels=width,
        height_pixels=height,
    )

    return layout, placements, column_heights


def _validate_options(options: GridOptions) -> None:
    if not 50 <= options.individual_image_size <= 3000:
        raise InvalidImageGridRequest("Image size must be between 50 and 3000 pixels.")

    if options.max_output_pixels <= 0:
        raise InvalidImageGridRequest("Maximum output size must be greater than zero.")

    if len(options.background_color) != 3:
        raise InvalidImageGridRequest("Background color must contain RGB values.")


def _validate_image_count(image_count: int) -> None:
    if image_count <= 0:
        raise InvalidImageGridRequest("Select at least one image.")


def _validate_output_size(layout: GridLayout, options: GridOptions) -> None:
    if layout.pixel_count <= options.max_output_pixels:
        return

    megapixels = layout.pixel_count / 1_000_000
    max_megapixels = options.max_output_pixels / 1_000_000
    raise InvalidImageGridRequest(
        "Requested grid is too large "
        f"({megapixels:.0f} MP). Reduce image size or split the batch "
        f"so the output stays under {max_megapixels:.0f} MP."
    )


def _order_items(items: List[T], options: GridOptions) -> None:
    if not options.randomized_order:
        return

    if options.random_seed is None:
        random.SystemRandom().shuffle(items)
        return

    random.Random(options.random_seed).shuffle(items)


def _make_tile(
    stream: BinaryIO,
    filename: str,
    cell_size: int,
    background_color: Tuple[int, int, int],
    stretch_to_square: bool,
) -> Image.Image:
    if _is_heif_filename(filename) and not HEIF_SUPPORT_ENABLED:
        raise InvalidImageFile(
            f"{filename} is a HEIC/HEIF image, but HEIC support is not installed. "
            "Run pip install -r backend/requirements.txt and restart the backend."
        )

    try:
        with Image.open(stream) as image:
            image = ImageOps.exif_transpose(image)
            image = _normalize_mode(image)
            if stretch_to_square:
                image = image.resize((cell_size, cell_size), RESAMPLE_FILTER)
            else:
                image.thumbnail((cell_size, cell_size), RESAMPLE_FILTER, reducing_gap=3.0)

            tile = Image.new("RGB", (cell_size, cell_size), background_color)
            x = (cell_size - image.width) // 2
            y = (cell_size - image.height) // 2

            if image.mode == "RGBA":
                tile.paste(image.convert("RGB"), (x, y), image.getchannel("A"))
            else:
                tile.paste(image, (x, y))

            return tile
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise InvalidImageFile(f"{filename} is not a readable image.") from exc


def _make_collage_tile(
    stream: BinaryIO,
    filename: str,
    width: int,
    height: int,
) -> Image.Image:
    if _is_heif_filename(filename) and not HEIF_SUPPORT_ENABLED:
        raise InvalidImageFile(
            f"{filename} is a HEIC/HEIF image, but HEIC support is not installed. "
            "Run pip install -r backend/requirements.txt and restart the backend."
        )

    try:
        with Image.open(stream) as image:
            image = ImageOps.exif_transpose(image)
            image = _normalize_mode(image)
            return image.resize((width, height), RESAMPLE_FILTER)
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise InvalidImageFile(f"{filename} is not a readable image.") from exc


def _image_aspect_ratio(stream: BinaryIO, filename: str) -> float:
    if _is_heif_filename(filename) and not HEIF_SUPPORT_ENABLED:
        raise InvalidImageFile(
            f"{filename} is a HEIC/HEIF image, but HEIC support is not installed. "
            "Run pip install -r backend/requirements.txt and restart the backend."
        )

    try:
        with Image.open(stream) as image:
            image = ImageOps.exif_transpose(image)
            if image.height <= 0:
                raise ValueError("Image height must be greater than zero.")

            return image.width / image.height
    except (OSError, UnidentifiedImageError, ValueError) as exc:
        raise InvalidImageFile(f"{filename} is not a readable image.") from exc


def _paste_image(canvas: Image.Image, image: Image.Image, xy: Tuple[int, int]) -> None:
    if image.mode == "RGBA":
        canvas.paste(image, xy, image.getchannel("A"))
    else:
        canvas.paste(image, xy)


def _output_paths(output_directory: Path) -> Tuple[Path, str]:
    timestamp = dt.datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
    download_name = f"{timestamp}_image_grid.png"
    output_path = output_directory / f"{timestamp}_{uuid4().hex[:8]}_image_grid.png"
    return output_path, download_name


def _is_heif_filename(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in HEIF_EXTENSIONS


def _normalize_mode(image: Image.Image) -> Image.Image:
    has_alpha = image.mode in {"RGBA", "LA"} or (
        image.mode == "P" and "transparency" in image.info
    )

    if has_alpha:
        return image.convert("RGBA")

    if image.mode != "RGB":
        return image.convert("RGB")

    return image


def _orientation_penalty(columns: int, rows: int, target_aspect_ratio: float) -> int:
    if target_aspect_ratio >= 1:
        return 0 if columns >= rows else 1

    return 0 if rows >= columns else 1


@contextmanager
def _open_existing_stream(stream: BinaryIO) -> Iterator[BinaryIO]:
    try:
        stream.seek(0)
    except (AttributeError, OSError):
        pass

    yield stream
