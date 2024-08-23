import json, time
import os, copy
import urllib.parse as urlparse
import threading
from multiprocessing import cpu_count
from pathlib import Path

import fitz
import requests
from bs4 import BeautifulSoup
from PIL import Image
from tqdm import tqdm


class BaseMangaSeriesScrapper:
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246"
    }
    BATCH_SIZE = 100
    # MAX_THREADS = 10
    MAX_THREADS = max(2, cpu_count() - 2)

    @property
    def OUTPUT_DIR(self):
        return Path(f"./downloads/") / self.NAME

    def __init__(
        self,
        url: str,
        skip_chapter_in_json: bool = True,
    ) -> None:
        """
        - `skip_chapter_in_json`: skip chapter scraping if its already in the json, default: `True`
        if `skip_chapter_in_json` is `True`, then it goes ahead with scrapping page and pdf verification        -
        """

        self.url: str = url
        self.skip_chapter_in_json: bool = skip_chapter_in_json

        ######################

        self.hostname = urlparse.urlparse(self.url).hostname

        parts = self.url.strip("/").split("/")
        self.manga_name = parts[-1]

        self.manga_dir = self.OUTPUT_DIR / self.manga_name
        os.makedirs(self.manga_dir, exist_ok=True)

        self.chapters_fp = self.manga_dir / "chapters.json"

        self.chapters_data = {}

        if os.path.exists(self.chapters_fp):
            try:
                with open(self.chapters_fp, encoding="utf-8") as f:
                    self.chapters_data = json.load(f)
            except Exception as err:
                print(err)

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

        _desc = f"{self.manga_name} ({self.NAME})"
        for ch_idx, url in tqdm(list(enumerate(urls, 1)), postfix=_desc):
            parts = url.strip("/").split("/")

            if len(parts) != 6:
                break

            chapter_prefix_idx = f"{str(ch_idx).zfill(self.index_width)}"
            chapter_name = f"{chapter_prefix_idx}__{parts[-1]}"

            if self.skip_chapter_in_json and url in [
                e["url"] for e in self.chapters_data.copy().values()
            ]:
                continue

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
        del self.chapters_data

    def process_page(self, url: str, ch_idx: int, chapter_name: str):
        imgs = self.get_imgs_from_url(url)

        batch_name = self.get_batch_name(ch_idx)

        if len(imgs) == 0:
            return

        imgs_width = len(str(len(imgs)))

        output_dir = self.manga_dir / "imgs" / batch_name / chapter_name
        pdf_fp = self.manga_dir / "pdfs" / batch_name / (chapter_name + ".pdf")

        for dpath in [output_dir, pdf_fp.parent]:
            os.makedirs(dpath, exist_ok=True)

        if (
            len(os.listdir(output_dir)) == len(imgs)
            and self.is_valid_fp(pdf_fp)
            and self.get_pdf_page_count(pdf_fp) == len(imgs)
        ):
            return

        images = []
        for idx, img in list(enumerate(imgs)):
            img_path = output_dir / (
                f"""{str(idx).zfill(imgs_width)}"""
                "."
                f"""{img.strip("/").split(".")[-1]}"""
            )

            if not (self.is_valid_fp(img_path)):
                try:
                    time.sleep(0.01)
                    img_resp = requests.get(
                        img,
                        headers=self.HEADERS,
                        allow_redirects=True,
                    )

                    if img_resp.status_code != 200:
                        continue

                    if img_resp.headers["Content-Type"].startswith("image"):
                        os.makedirs(img_path.parent, exist_ok=True)
                        with open(img_path, "wb") as f:
                            f.write(img_resp.content)
                    else:
                        print(img_resp.headers["Content-Type"])
                        print(img_resp.text)

                    del img_resp

                    images.append(self.get_img(img_path))
                except:
                    pass

        self.convert_imgs2pdf(images, pdf_fp)
        del images

        self.chapters_data[chapter_name] = {
            "chapter_index": ch_idx,
            "url": url,
            "image_urls": imgs,
        }

    def convert_imgs2pdf(self, images: list, fp: Path):
        if len(images) > 0:
            images[0].save(
                fp,
                save_all=True,
                append_images=images,
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

    def get_all_chapter_urls(self):
        raise NotImplementedError()

    def get_imgs_from_url(self, url: str):
        raise NotImplementedError()
