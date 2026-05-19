from pathlib import Path

from image_grid import GridOptions, generate_image_grid_from_paths, is_supported_filename


def grid_images(
    input_folder,
    base_directory_name,
    outputs_directory,
    individual_image_size=1000,
    randomized_order=True,
    printer_paper_format=False,
):
    """Backward-compatible wrapper for older scripts that imported grid_images."""
    _ = base_directory_name
    input_folder = Path(input_folder)
    image_paths = [
        path
        for path in input_folder.iterdir()
        if path.is_file() and is_supported_filename(path.name)
    ]

    options = GridOptions(
        individual_image_size=individual_image_size,
        randomized_order=randomized_order,
        printer_paper_format=printer_paper_format,
    )
    generated_grid = generate_image_grid_from_paths(
        image_paths=image_paths,
        output_directory=outputs_directory,
        options=options,
    )

    return str(generated_grid.path)
