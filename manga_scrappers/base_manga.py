import time, json
import os, threading
from multiprocessing import cpu_count
from pathlib import Path
from tqdm import tqdm

import requests
from PIL import Image

from base import BaseScrapper


class BaseMangaScrapper(BaseScrapper):
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

    def scrap(self):
        urls = self.get_all_chapter_urls()
        with open(self.manga_dir / "chapter_urls.json", "w") as f:
            json.dump(
                urls, f, ensure_ascii=False, indent=4, sort_keys=True, default=str
            )

        self.index_width = max(5, len(str(len(urls))))

        threads = []

        _desc = f"{self.name} ({self.NAME})"
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

        print(self.name, len(self.new_chapters))

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

        self.new_chapters.add(url)
        self.chapters_data[chapter_name] = {
            "chapter_index": ch_idx,
            "url": url,
            "image_urls": imgs,
        }

    def get_imgs_from_url(self, url: str):
        raise NotImplementedError()
