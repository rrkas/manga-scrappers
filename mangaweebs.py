import json
import os
import shutil
import sys
from pathlib import Path
from PIL import Image

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from tqdm import tqdm
from selenium.webdriver.chrome.service import Service


def set_chrome_options():
    chrome_options = Options()
    for e in [
        "enable-automation",
        "start-maximized",
        "disable-infobars",
        "--disable-infobars",
        # "--headless",
        "--no-sandbox",
        "--force-device-scale-factor=1",
        "--disable-extensions",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-logging",
    ]:
        chrome_options.add_argument(e)

    # chrome_prefs = {"profile.managed_default_content_settings.images": 2}
    # chrome_options.experimental_options["prefs"] = chrome_prefs
    # chrome_prefs["profile.default_content_settings"] = {"images": 2}
    # chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    return chrome_options


def get_driver(url):
    # start = datetime.datetime.now()
    # service = Service(executable_path="/usr/bin/chromedriver")
    driver = webdriver.Chrome(
        # service=service,
        options=set_chrome_options(),
    )
    # driver = webdriver.Remote(desired_capabilities=webdriver.DesiredCapabilities.HTMLUNIT)
    driver.implicitly_wait(0.05)
    driver.set_page_load_timeout(60 * 60 * 60)
    driver.get(url)
    # end = datetime.datetime.now()
    # print(end - start)
    return driver


output_dir = Path("data/mangaclash")
os.makedirs(output_dir, exist_ok=True)


url = sys.argv[1]

ch_idx = 1

parts = url.strip("/").split("/")
manga_name = parts[-2]
manga_dir = output_dir / manga_name
raw_imgs_dir = output_dir / manga_name / "raw_imgs"
os.makedirs(manga_dir, exist_ok=True)
os.makedirs(raw_imgs_dir, exist_ok=True)
pdfs_dir = output_dir / manga_name / manga_name
os.makedirs(pdfs_dir, exist_ok=True)

chapters_data = {}


def get_img(path: Path):
    if path.name.split(".")[-1] == "png":
        png = Image.open(path)
        png.load()  # required for png.split()
        background = Image.new(
            "RGB",
            png.size,
            (255, 255, 255),
        )
        pngLayers = png.split()
        background.paste(
            png,
            mask=pngLayers[3] if len(pngLayers) > 3 else None,
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

    driver = get_driver(url)

    imgs = []

    for e in driver.find_elements(By.XPATH, """//*[@class="reading-content"]//img"""):
        iurl = e.get_attribute("src")

        if "logo." in iurl:
            continue

        imgs.append(iurl)

    if len(imgs) != 0:
        imgs_width = len(str(len(imgs)))

        chapters_data[str(ch_idx).zfill(5)] = {
            "chapter_index": ch_idx,
            "url": url,
            "image_urls": imgs,
        }

        pdf_fp = pdfs_dir / (chapter_name + ".pdf")
        if not (os.path.exists(pdf_fp) and os.stat(pdf_fp).st_size > 0):
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
                # print(img)
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

                img_resp = requests.get(img, allow_redirects=True)

                if img_resp.headers["Content-Type"].startswith("image"):
                    os.makedirs(img_path.parent, exist_ok=True)
                    with open(img_path, "wb") as f:
                        f.write(img_resp.content)

                    images.append(get_img(img_path))
                else:
                    print(img_resp.headers["Content-Type"])
                    print(img_resp.text)
                    exit()

            if len(images) > 0:
                if not (os.path.exists(pdf_fp) and os.stat(pdf_fp).st_size > 0):
                    images[0].save(
                        pdf_fp,
                        save_all=True,
                        append_images=images[1:],
                    )

                # shutil.make_archive(
                #     raw_imgs_dir / chapter_name,
                #     "zip",
                #     raw_imgs_dir / chapter_name,
                # )

                shutil.rmtree(raw_imgs_dir / chapter_name)

    next_btn = driver.find_elements(By.XPATH, """//*[@class="btn next_page"]""")
    # next_btn.get_attribute("href")

    if len(next_btn) == 0:
        break

    url = next_btn[0].get_attribute("href")

    ch_idx += 1

    # break
