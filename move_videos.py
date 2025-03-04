import os
import shutil
import re
import argparse
import logging

# Configure logging to output time, level, and message
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Define your source and destination directories
origin_folder = r"C:\Users\Lenovoç\Videos\done2"
destination_root = r"E:\MadBoulder\Uploaded"

def extract_area(file_name):
    """
    Extracts the area name from a file name.
    Expected filename formats:
      - "{boulder name}, {grade}. {area}"
      - "{boulder name}. {area}"
    Logs the process and returns the extracted area.
    """
    logging.info(f"Extracting area from file: {file_name}")
    base_name, _ = os.path.splitext(file_name)
    match = re.search(r'\.\s*(.+)$', base_name)
    if match:
        area = match.group(1).strip()
        logging.info(f"Extracted area: {area}")
        return area
    logging.warning(f"Could not extract area from file: {file_name}")
    return None

def find_target_folder(area):
    """
    Searches through country folders in the destination root to locate a folder named with the area.
    Returns the folder path if found, or None if not.
    """
    logging.info(f"Looking for target folder for area: {area}")
    for country in os.listdir(destination_root):
        country_path = os.path.join(destination_root, country)
        if os.path.isdir(country_path):
            area_path = os.path.join(country_path, area)
            if os.path.isdir(area_path):
                logging.info(f"Found existing folder: {area_path} (inside '{country}')")
                return area_path
    logging.info(f"No existing folder found for area '{area}' under any country folder.")
    return None

def process_file(file, origin_folder, destination_root):
    """
    Processes a single file: extracts the area, finds or creates the destination folder,
    and moves the file.
    """
    file_path = os.path.join(origin_folder, file)
    if not os.path.isfile(file_path):
        logging.warning(f"Skipping '{file}': not a file")
        return
    logging.info(f"Processing file: {file}")

    area = extract_area(file)
    if not area:
        logging.warning(f"Skipping '{file}': could not extract area name.")
        return

    target_folder = find_target_folder(area)
    if not target_folder:
        # Create a new folder under the destination root if no area folder exists in any country folder.
        target_folder = os.path.join(destination_root, area)
        os.makedirs(target_folder, exist_ok=True)
        logging.info(f"Created new folder: {target_folder}")

    destination_file = os.path.join(target_folder, file)
    logging.info(f"Moving file '{file}' to '{destination_file}'")
    shutil.move(file_path, destination_file)
    logging.info(f"File '{file}' moved successfully.")

def main():
    parser = argparse.ArgumentParser(
        description="Move files from the origin folder to an area folder on the external hard drive."
    )
    parser.add_argument(
        '--file',
        help="Specify one file to process (must exist in the origin folder).",
        default=None
    )
    args = parser.parse_args()

    if args.file:
        # Process only the specified file.
        single_file_path = os.path.join(origin_folder, args.file)
        if os.path.exists(single_file_path):
            logging.info(f"Processing single file: {args.file}")
            process_file(args.file, origin_folder, destination_root)
        else:
            logging.error(f"File '{args.file}' does not exist in the origin folder '{origin_folder}'.")
    else:
        # Process all files in the origin folder.
        files = os.listdir(origin_folder)
        logging.info(f"Found {len(files)} items in the origin folder '{origin_folder}'. Processing all files.")
        for file in files:
            process_file(file, origin_folder, destination_root)

if __name__ == "__main__":
    main()
