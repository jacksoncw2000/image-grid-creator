import os
import tkinter as tk
from tkinter import filedialog


def ensure_directory_exists(directory_path):
    """
    Desc:
        Ensures a directory exists at the specified path. If it doesn't, the directory is created.
    Args:
        directory_path (str): The path of the directory to ensure exists.
    Returns:
        None
    """
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"[INFO] Directory created at {directory_path}")


def str_to_bool(value):
    return value.lower() in ('true', 't', 'yes', 'y', '1')


def select_folder():
    """
    Desc:
        Opens a file dialog to allow the user to select a folder.
        The last selected folder is saved and opened the next time.
    Args:
        None
    Returns:
        str: The path of the selected folder.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the main window

    # Define the absolute path to the last_folder.txt file
    last_folder_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_folder.txt")
    #print(f"[INFO] last_folder.txt is being saved to: {last_folder_file}")

    # Read the last selected folder from a file
    last_folder_path = ""
    if os.path.exists(last_folder_file):
        with open(last_folder_file, "r") as file:
            last_folder_path = file.read().strip()

    # Open the directory chooser with the last selected folder
    folder_path = filedialog.askdirectory(initialdir=last_folder_path)

    # Save the selected folder path to a file
    with open(last_folder_file, "w") as file:
        file.write(folder_path)

    return folder_path