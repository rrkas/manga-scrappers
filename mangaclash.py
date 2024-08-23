import traceback
import sys
from base import BaseMangaSeriesScrapper


class MangaClashMangaSeriesScrapper(BaseMangaSeriesScrapper):
    NAME = "MangaClash".lower()

    def get_all_chapter_urls(self):
        soup = self.get_soup(self.url)
        return [
            e.find("a")["href"]
            for e in soup.find_all("li", attrs={"class": "wp-manga-chapter"})
        ][::-1]

    def get_imgs_from_url(self, url: str):
        imgs = []
        soup = self.get_soup(url)
        imgs_div = soup.find("div", attrs={"class": "reading-content"})

        if imgs_div is None:
            return imgs

        for e in imgs_div.findAll("img"):
            try:
                imgs.append(e["src"].strip())
            except:
                try:
                    imgs.append(e["data-src"].strip())
                except:
                    pass

        imgs = [e for e in imgs if "logo." not in e]
        return imgs


if __name__ == "__main__":
    BASE_URL = sys.argv[1]
    scrapper = MangaClashMangaSeriesScrapper(BASE_URL)
    try:
        scrapper.scrap()
    except Exception as err:
        print("ERR", BASE_URL, str(err).splitlines()[0])
        traceback.print_exc()
