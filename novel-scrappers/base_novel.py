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

from base import BaseScrapper


class BaseNovelScrapper(BaseScrapper):
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

        print(self.manga_name, len(self.new_chapters))

    def process_page(self, url: str, ch_idx: int, chapter_name: str):
        txt = self.get_txt_from_url(url)

        batch_name = self.get_batch_name(ch_idx)

        if txt is None or len(txt) == 0:
            return

        imgs_width = len(str(len(txt)))

        raw_output_fp = (
            self.manga_dir / "raw_txt" / batch_name / (chapter_name + ".txt")
        )
        pdf_fp = self.manga_dir / "pdfs" / batch_name / (chapter_name + ".pdf")

        for dpath in [raw_output_fp, pdf_fp.parent]:
            os.makedirs(dpath, exist_ok=True)

        if (
            len(os.listdir(raw_output_fp)) == len(txt)
            and self.is_valid_fp(pdf_fp)
            and self.get_pdf_page_count(pdf_fp) == len(txt)
        ):
            return

        images = []
        for idx, img in list(enumerate(txt)):
            img_path = raw_output_fp / (
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

        self.new_chapters.add(url)
        self.chapters_data[chapter_name] = {
            "chapter_index": ch_idx,
            "url": url,
            "image_urls": txt,
        }

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

    def get_txt_from_url(self, url: str):
        raise NotImplementedError()
