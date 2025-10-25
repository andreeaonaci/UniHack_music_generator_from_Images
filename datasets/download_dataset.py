import xml.etree.ElementTree as ET
import os
import csv
import requests

XML_PATH = "datasets/dataset.xml"
IMAGES_DIR = "datasets/images"
CSV_PATH = "datasets/metadata.csv"

os.makedirs(IMAGES_DIR, exist_ok=True)

tree = ET.parse(XML_PATH)
root = tree.getroot()

with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["title", "description", "image_path"])

    for photo in root.findall("photo"):
        title = photo.find("title").text or "Unknown"
        description = photo.find("description").text or ""
        image_url = photo.find("image_url").text if photo.find("image_url") is not None else None

        if not image_url:
            continue

        try:
            safe_title = title.replace(" ", "_").replace("/", "_")
            img_path = os.path.join(IMAGES_DIR, f"{safe_title}.jpg")

            response = requests.get(image_url, timeout=10)
            if response.status_code == 200:
                with open(img_path, "wb") as img_file:
                    img_file.write(response.content)

                writer.writerow([title, description, img_path])
                print(f"✅ Saved: {img_path}")
            else:
                print(f"⚠️ Failed: {image_url}")

        except Exception as e:
            print(f"⚠️ Error downloading: {image_url} | {str(e)}")
