import json
import os
import shutil
import sys
import threading
from pathlib import Path
from multiprocessing import cpu_count
import requests
from bs4 import BeautifulSoup
from PIL import Image
from tqdm import tqdm


class MangaClashMangaSeriesScrapper:
    OUTPUT_DIR = Path("data/mangaclash")
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            + "AppleWebKit/537.36 (KHTML, like Gecko) "
            + "Chrome/42.0.2311.135 "
            + "Safari/537.36 "
            + "Edge/12.246"
        )
    }
    BATCH_SIZE = 100
    INDEX_WIDTH = 5
    MAX_THREADS = 3
    # MAX_THREADS = max(1, cpu_count() // 2)

    def __init__(self, base_url) -> None:
        self.url = base_url

        parts = self.url.strip("/").split("/")
        self.manga_name = parts[-2]

        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

        self.manga_dir = self.OUTPUT_DIR / self.manga_name
        os.makedirs(self.manga_dir, exist_ok=True)

        self.raw_imgs_dir = self.OUTPUT_DIR / self.manga_name / "raw_imgs"
        os.makedirs(self.raw_imgs_dir, exist_ok=True)

        self.pdfs_dir = self.OUTPUT_DIR / self.manga_name / self.manga_name
        os.makedirs(self.pdfs_dir, exist_ok=True)

        self.chapters_fp = self.manga_dir / "chapters.json"

        self.chapters_data = {}

        if os.path.exists(self.chapters_fp):
            with open(self.chapters_fp, encoding="utf-8") as f:
                self.chapters_data = json.load(f)

    def get_img(self, path: Path):
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

    def is_valid_fp(self, fp: Path):
        return os.path.exists(fp) and os.stat(fp).st_size > 0

    def get_batch_name(self, idx):
        _min = ((idx - 1) // self.BATCH_SIZE) * self.BATCH_SIZE + 1
        _max = _min + self.BATCH_SIZE - 1
        return (
            f"{str(_min).zfill(self.INDEX_WIDTH)}"
            f"-"
            f"{str(_max).zfill(self.INDEX_WIDTH)}"
        )

    def get_soup(self, url):
        resp = requests.get(url, headers=self.HEADERS)
        return BeautifulSoup(resp.content, "html5lib")

    def scrap(self):
        ch_idx = 1
        url = self.url

        threads = []

        while True:
            parts = url.strip("/").split("/")

            if len(parts) != 6:
                break

            chapter_name = f"""{str(ch_idx).zfill(self.INDEX_WIDTH)}__{parts[-1]}"""

            print(url)
            soup = self.get_soup(url)

            if chapter_name not in self.chapters_data:
                t = threading.Thread(
                    target=self.process_page,
                    kwargs=dict(
                        url=url,
                        ch_idx=ch_idx,
                        chapter_name=chapter_name,
                    ),
                )
                t.start()
                threads.append(t)

            next_btn = soup.find("div", attrs={"class": "nav-next"})

            if next_btn is None:
                break

            url = next_btn.a["href"]

            ch_idx += 1

            while sum([t.is_alive() for t in threads]) >= self.MAX_THREADS:
                pass

        while any([t.is_alive() for t in threads]):
            pass

        os.system(f""" rm -rf "{self.raw_imgs_dir}" """)

    def process_page(
        self,
        url: str,
        ch_idx: int,
        chapter_name: str,
    ):
        soup = self.get_soup(url)
        imgs_div = soup.find("div", attrs={"class": "reading-content"})
        batch_name = self.get_batch_name(ch_idx)

        if imgs_div is None:
            return

        imgs = []
        for e in imgs_div.findAll("img"):
            try:
                imgs.append(e["src"].strip())
            except:
                try:
                    imgs.append(e["data-src"].strip())
                except:
                    pass

        imgs = [e for e in imgs if "logo." not in e]

        self.chapters_data[chapter_name] = {
            "chapter_index": ch_idx,
            "url": url,
            "image_urls": imgs,
        }

        with open(self.chapters_fp, "w", encoding="utf-8") as f:
            json.dump(
                self.chapters_data,
                f,
                indent=4,
                default=str,
                sort_keys=True,
                ensure_ascii=True,
            )

        if len(imgs) == 0:
            return

        imgs_width = len(str(len(imgs)))

        pdf_fp = self.pdfs_dir / batch_name / (chapter_name + ".pdf")
        os.makedirs(pdf_fp.parent, exist_ok=True)

        if self.is_valid_fp(pdf_fp):
            return

        images = []
        for idx, img in tqdm(list(enumerate(imgs))):
            # print(img)
            img_path = (
                self.raw_imgs_dir
                / batch_name
                / chapter_name
                / (
                    f"""{str(idx).zfill(imgs_width)}"""
                    "."
                    f"""{img.strip("/").split(".")[-1]}"""
                )
            )

            if not (self.is_valid_fp(img_path)):
                try:
                    img_resp = requests.get(
                        img,
                        headers=self.HEADERS,
                        allow_redirects=True,
                    )

                    if img_resp.headers["Content-Type"].startswith("image"):
                        os.makedirs(img_path.parent, exist_ok=True)
                        with open(img_path, "wb") as f:
                            f.write(img_resp.content)
                    else:
                        print(img_resp.headers["Content-Type"])
                        print(img_resp.text)
                        exit()
                except:
                    pass

            try:
                images.append(self.get_img(img_path))
            except:
                pass

        self.convert_imgs2pdf(images, pdf_fp)

    def convert_imgs2pdf(self, images: list, fp: Path):
        if len(images) > 0:
            print(fp)
            images[0].save(
                fp,
                save_all=True,
                append_images=images[1:],
            )


scrapper = MangaClashMangaSeriesScrapper(sys.argv[1])
scrapper.scrap()
