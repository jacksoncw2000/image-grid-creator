from pathlib import Path


TRUE_VALUES = {"1", "t", "true", "y", "yes", "on"}


def ensure_directory_exists(directory_path):
    Path(directory_path).mkdir(parents=True, exist_ok=True)


def str_to_bool(value):
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    return str(value).strip().lower() in TRUE_VALUES


def select_folder():
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()

    last_folder_file = Path(__file__).resolve().with_name("last_folder.txt")
    last_folder_path = last_folder_file.read_text().strip() if last_folder_file.exists() else ""

    folder_path = filedialog.askdirectory(initialdir=last_folder_path)
    last_folder_file.write_text(folder_path)

    return folder_path
