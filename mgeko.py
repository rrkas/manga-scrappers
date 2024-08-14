import json, time
import os, traceback
import sys
import threading
import uuid
from multiprocessing import cpu_count
from pathlib import Path

import fitz
import requests
from bs4 import BeautifulSoup
from PIL import Image
from tqdm import tqdm


class MgekoMangaSeriesScrapper:
    OUTPUT_DIR = Path("data/mgeko")
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246"
    }
    BATCH_SIZE = 100
    # MAX_THREADS = 10
    MAX_THREADS = max(1, cpu_count() - 1)

    def __init__(self, url) -> None:
        self.url = url

        parts = self.url.strip("/").split("/")
        self.manga_name = parts[-1]

        self.raw_imgs_dir = self.OUTPUT_DIR / ".temp" / str(uuid.uuid4().hex)
        os.makedirs(self.raw_imgs_dir, exist_ok=True)

        self.manga_dir = self.OUTPUT_DIR / self.manga_name
        os.makedirs(self.manga_dir, exist_ok=True)

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

    def get_pdf_page_count(self, fp: Path):
        pdf_document = fitz.open(str(fp))
        num_pages = pdf_document.page_count
        pdf_document.close()
        return num_pages

    def is_valid_fp(self, fp: Path):
        return os.path.exists(fp) and os.stat(fp).st_size > 0

    def get_batch_name(self, idx):
        _min = ((idx - 1) // self.BATCH_SIZE) * self.BATCH_SIZE + 1
        _max = _min + self.BATCH_SIZE - 1
        return (
            f"{str(_min).zfill(self.index_width)}"
            f"-"
            f"{str(_max).zfill(self.index_width)}"
        )

    def get_soup(self, url):
        resp = requests.get(url, headers=self.HEADERS)
        return BeautifulSoup(resp.content, "html5lib")

    def scrap(self):
        urls = self.get_all_chapter_urls()
        with open(self.manga_dir / "chapter_urls.json", "w") as f:
            json.dump(
                urls, f, ensure_ascii=False, indent=4, sort_keys=True, default=str
            )

        self.index_width = max(5, len(str(len(urls))))

        threads = []

        for ch_idx, url in tqdm(list(enumerate(urls, 1)), desc=self.url):
            parts = url.strip("/").split("/")

            if len(parts) != 6:
                break

            chapter_name = f"""{str(ch_idx).zfill(self.index_width)}__{parts[-1]}"""

            # print(url)

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

            if ch_idx % self.MAX_THREADS == 0:
                self.save_chapters()

            while sum([t.is_alive() for t in threads]) >= self.MAX_THREADS:
                pass

        while any([t.is_alive() for t in threads]):
            pass

        self.save_chapters()

        os.system(f""" rm -rf "{self.raw_imgs_dir}" """)

    def get_all_chapter_urls(self):
        soup = self.get_soup(self.url)
        return [
            e.find("a")["href"]
            for e in soup.find_all("li", attrs={"class": "wp-manga-chapter"})
        ][::-1]

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

        if len(imgs) == 0:
            return

        imgs_width = len(str(len(imgs)))

        pdf_fp = self.manga_dir / batch_name / (chapter_name + ".pdf")
        os.makedirs(pdf_fp.parent, exist_ok=True)

        if self.is_valid_fp(pdf_fp) and self.get_pdf_page_count(pdf_fp) == len(imgs):
            return

        images = []
        for idx, img in list(enumerate(imgs)):
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
                    time.sleep(0.01)
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
        os.system(f'rm -rf "{self.raw_imgs_dir / batch_name / chapter_name}"')

    def convert_imgs2pdf(self, images: list, fp: Path):
        if len(images) > 0:
            # print(fp)
            images[0].save(
                fp,
                save_all=True,
                append_images=images[1:],
            )

    def save_chapters(self):
        with open(self.chapters_fp, "w", encoding="utf-8") as f:
            json.dump(
                self.chapters_data,
                f,
                indent=4,
                default=str,
                sort_keys=True,
                ensure_ascii=True,
            )


if __name__ == "__main__":
    BASE_URL = sys.argv[1]
    scrapper = MgekoMangaSeriesScrapper(BASE_URL)
    try:
        scrapper.scrap()
    except Exception as err:
        print("ERR", BASE_URL, str(err).splitlines()[0])
        traceback.print_exc()
