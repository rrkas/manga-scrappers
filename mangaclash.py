import json
import os
import sys
from pathlib import Path
from PIL import Image

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

output_dir = Path("data/mangaclash")
os.makedirs(output_dir, exist_ok=True)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246"
}

url = sys.argv[1]

ch_idx = 1

parts = url.strip("/").split("/")
manga_name = parts[-2]
manga_dir = output_dir / manga_name
raw_imgs_dir = output_dir / manga_name / "raw_imgs"
pdfs_dir = output_dir / manga_name / "pdfs"
os.makedirs(manga_dir, exist_ok=True)
os.makedirs(raw_imgs_dir, exist_ok=True)
os.makedirs(pdfs_dir, exist_ok=True)

chapters_data = {}


def get_img(path: Path):
    if path.name.split(".")[-1] == "png":
        png = Image.open(path)
        png.load()  # required for png.split()
        background = Image.new("RGB", png.size, (255, 255, 255))
        pngLayers = png.split()
        background.paste(
            png, mask=pngLayers[3] if len(pngLayers) > 3 else None
        )  # 3 is the alpha channel
        return background
    else:
        img = Image.open(path)
        img.convert()
        return img


while True:
    parts = url.strip("/").split("/")

    if len(parts) != 6:
        break

    chapter_name = f"""{str(ch_idx).zfill(5)}__{parts[-1]}"""

    print(url)
    resp = requests.get(url, headers=headers)
    soup = BeautifulSoup(resp.content, "html5lib")

    imgs_div = soup.find("div", attrs={"class": "reading-content"})

    if imgs_div is None:
        break

    imgs = [e["data-src"].strip() for e in imgs_div.findAll("img")]

    imgs_width = len(str(len(imgs)))

    chapters_data[str(ch_idx).zfill(5)] = {
        "chapter_index": ch_idx,
        "url": url,
        "image_urls": imgs,
    }

    with open(manga_dir / "chapters.json", "w", encoding="utf-8") as f:
        json.dump(
            chapters_data,
            f,
            indent=4,
            default=str,
            ensure_ascii=True,
        )

    images = []
    for idx, img in tqdm(list(enumerate(imgs))):
        img_path = (
            raw_imgs_dir
            / chapter_name
            / (
                f"""{str(idx).zfill(imgs_width)}"""
                "."
                f"""{img.strip("/").split(".")[-1]}"""
            )
        )

        if os.path.exists(img_path) and os.stat(img_path).st_size > 0:
            continue

        img_resp = requests.get(img)
        os.makedirs(img_path.parent, exist_ok=True)
        with open(img_path, "wb") as f:
            f.write(img_resp.content)

        images.append(get_img(img_path))

    pdf_fp = pdfs_dir / (chapter_name + ".pdf")
    if not (os.path.exists(pdf_fp) and os.stat(pdf_fp).st_size > 0):
        images[0].save(
            pdf_fp,
            save_all=True,
            append_images=images[1:],
        )

    next_btn = soup.find("div", attrs={"class": "nav-next"})

    if next_btn is None:
        break

    url = next_btn.a["href"]

    ch_idx += 1

    # break
