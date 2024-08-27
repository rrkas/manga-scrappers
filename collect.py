# 2023 dec 12

from manga_scrappers import mangaclash, mgeko, urls as manga_urls
import threading

MAX_THREADS = 1
skip_chapter_in_json = True
threads = []

#########################################################################
#                          Mangaclash                                   #
#########################################################################


def process_mc(url):
    try:
        obj = mangaclash.MangaClashMangaSeriesScrapper(
            url,
            skip_chapter_in_json=skip_chapter_in_json,
        )
        obj.scrap()
        del obj
    except Exception as err:
        print("ERR", url, str(err).splitlines()[0])


for url in sorted(manga_urls.mangaclash_urls, key=len):
    t = threading.Thread(target=process_mc, args=(url,))
    t.start()
    threads.append(t)

    while sum([t.is_alive() for t in threads]) >= MAX_THREADS:
        pass

#########################################################################
#                               mgeko                                   #
#########################################################################


def process_mg(url):
    try:
        obj = mgeko.MgekoMangaSeriesScrapper(
            url,
            skip_chapter_in_json=skip_chapter_in_json,
        )
        obj.scrap()
        del obj
    except Exception as err:
        print("ERR", url, str(err).splitlines()[0])


for url in sorted(manga_urls.mgeko_urls, key=len):
    t = threading.Thread(target=process_mg, args=(url,))
    t.start()
    threads.append(t)

    while sum([t.is_alive() for t in threads]) >= MAX_THREADS:
        pass

while sum([t.is_alive() for t in threads]) > 0:
    pass
