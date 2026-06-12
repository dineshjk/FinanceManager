# -*- coding: utf-8 -*-
# StockMan/search_me.py
import os
import zipfile


def search_text_in_zips(directory_path, search_string):
    print(
        f"Searching for '{search_string}' in .zip files within '{directory_path}'...\n"
    )
    found_count = 0

    # Walk through the directory and its subdirectories
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file.endswith(".zip"):
                zip_path = os.path.join(root, file)

                try:
                    # Open the zip file
                    with zipfile.ZipFile(zip_path, "r") as z:
                        # Check every file inside the archive
                        for internal_file in z.namelist():
                            # Filter to check only Python files to speed up the search
                            if internal_file.endswith(".py"):
                                with z.open(internal_file) as f:
                                    try:
                                        # Decode the bytes to string and search
                                        content = f.read().decode("utf-8")
                                        if search_string in content:
                                            print(f"✅ FOUND IN ZIP: {file}")
                                            print(
                                                f"   -> File: {internal_file}\n"
                                            )
                                            found_count += 1
                                    except UnicodeDecodeError:
                                        # Skip files that aren't standard text
                                        pass
                except zipfile.BadZipFile:
                    print(
                        f"⚠️ Warning: '{file}' is not a valid or readable ZIP file."
                    )

    if found_count == 0:
        print("No matches found.")
    else:
        print(f"Search complete. Found {found_count} instances.")


# --- RUN THE SCRIPT ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

backup_folder_path = project_root
target_string = "add_escape_binding"

search_text_in_zips(backup_folder_path, target_string)
