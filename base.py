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


class BaseScrapper:
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
        self.name = parts[-1]

        self.manga_dir = self.OUTPUT_DIR / self.name
        os.makedirs(self.manga_dir, exist_ok=True)

        self.chapters_fp = self.manga_dir / "chapters.json"

        self.chapters_data = {}

        self.new_chapters = set()

        if os.path.exists(self.chapters_fp):
            try:
                with open(self.chapters_fp, encoding="utf-8") as f:
                    self.chapters_data = json.load(f)
            except Exception as err:
                print(err)

    def get_soup(self, url):
        resp = requests.get(url, headers=self.HEADERS)
        return BeautifulSoup(resp.content, "html5lib")

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
        raise NotImplementedError()

    def process_page(self, url: str, ch_idx: int, chapter_name: str):
        raise NotImplementedError()

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
