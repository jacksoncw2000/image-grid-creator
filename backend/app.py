import logging
import os
from pathlib import Path

from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from image_grid import (
    DEFAULT_MAX_OUTPUT_PIXELS,
    SUPPORTED_EXTENSIONS,
    GridOptions,
    ImageGridError,
    ImageInput,
    generate_image_grid,
    is_supported_filename,
)
from utility.utils_general import str_to_bool


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MAX_UPLOAD_MB = 2048


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        MAX_CONTENT_LENGTH=_max_upload_bytes(),
        MAX_OUTPUT_PIXELS=_env_int("MAX_OUTPUT_PIXELS", DEFAULT_MAX_OUTPUT_PIXELS),
        OUTPUT_FOLDER=Path(os.getenv("OUTPUT_FOLDER", BASE_DIR / "outputs")),
    )

    if config:
        app.config.update(config)

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    app.logger.setLevel(logging.INFO)

    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_entity_too_large(error):
        limit_mb = app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024)
        return _json_error(
            f"Upload is too large. The current limit is {limit_mb:.0f} MB.",
            413,
            "upload_too_large",
        )

    @app.route("/")
    def home():
        return jsonify(
            {
                "message": "Image Grid API",
                "maxUploadMb": round(app.config["MAX_CONTENT_LENGTH"] / (1024 * 1024)),
                "supportedExtensions": sorted(SUPPORTED_EXTENSIONS),
            }
        )

    @app.route("/api/test", methods=["GET"])
    def test_route():
        return jsonify({"message": "Test successful"}), 200

    @app.route("/api/create-grid", methods=["POST"])
    def create_grid():
        try:
            image_inputs = _image_inputs_from_request()
            options = GridOptions(
                individual_image_size=_form_int("individualImageSize", 1000),
                randomized_order=str_to_bool(request.form.get("randomizedOrder", "true")),
                printer_paper_format=str_to_bool(request.form.get("printerPaperFormat", "false")),
                stretch_to_square=str_to_bool(request.form.get("stretchToSquare", "false")),
                max_output_pixels=app.config["MAX_OUTPUT_PIXELS"],
            )

            generated_grid = generate_image_grid(
                image_inputs=image_inputs,
                output_directory=app.config["OUTPUT_FOLDER"],
                options=options,
            )

            return _grid_file_response(generated_grid, app)
        except RequestEntityTooLarge:
            raise
        except ImageGridError as error:
            return _json_error(str(error), 400, "invalid_grid_request")
        except ValueError as error:
            return _json_error(str(error), 400, "invalid_form_value")
        except Exception:
            app.logger.exception("Unexpected error while creating image grid")
            return _json_error(
                "An unexpected error occurred while creating the grid.",
                500,
                "grid_generation_failed",
            )

    return app


def _image_inputs_from_request():
    if "files[]" not in request.files:
        raise ValueError("No files were uploaded.")

    files = [file for file in request.files.getlist("files[]") if file and file.filename]
    if not files:
        raise ValueError("No files were selected.")

    unsupported = [file.filename for file in files if not is_supported_filename(file.filename)]
    if unsupported:
        preview = ", ".join(unsupported[:5])
        suffix = "" if len(unsupported) <= 5 else f" and {len(unsupported) - 5} more"
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(
            f"Unsupported file type for {preview}{suffix}. Supported extensions: {supported}."
        )

    return [
        ImageInput(name=secure_filename(file.filename) or file.filename, stream=file.stream)
        for file in files
    ]


def _form_int(name, default):
    raw_value = request.form.get(name, default)
    try:
        return int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number.") from exc


def _json_error(message, status_code, code):
    return jsonify({"error": {"code": code, "message": message}}), status_code


def _grid_file_response(generated_grid, app):
    output_path = Path(generated_grid.path)
    headers = {
        "Content-Disposition": f"attachment; filename={generated_grid.download_name}",
        "Content-Length": str(output_path.stat().st_size),
        "Cache-Control": "no-cache",
    }

    return Response(
        _stream_file_then_cleanup(output_path, app),
        mimetype="image/png",
        headers=headers,
        direct_passthrough=True,
    )


def _stream_file_then_cleanup(path, app, chunk_size=1024 * 1024):
    try:
        with Path(path).open("rb") as file:
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    finally:
        _cleanup_file(path, app)


def _cleanup_file(path, app):
    try:
        Path(path).unlink()
    except FileNotFoundError:
        return
    except OSError:
        app.logger.warning("Could not remove temporary grid output %s", path)


def _max_upload_bytes():
    return _env_int("MAX_UPLOAD_MB", DEFAULT_MAX_UPLOAD_MB) * 1024 * 1024


def _env_int(name, default):
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        return int(raw_value)
    except ValueError:
        return default


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
