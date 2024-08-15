# 2023 dec 12

import mangaclash, mgeko

for url in [
    #
    #############
    # completed #
    #############
    #
    "https://mangaclash.com/manga/bleach/",
    "https://mangaclash.com/manga/naruto/",
    "https://mangaclash.com/manga/solo-leveling/",
    "https://mangaclash.com/manga/tomb-raider-king/",
    #
    ###########
    # ongoing #
    ###########
    #
    "https://mangaclash.com/manga/one-piece/",
    "https://mangaclash.com/manga/dragon-ball/",
    "https://mangaclash.com/manga/jujutsu-kaisen/",
    "https://mangaclash.com/manga/hunter-x-hunter/",
    "https://mangaclash.com/manga/the-beginning-after-the-end/",
]:
    try:
        mangaclash.MangaClashMangaSeriesScrapper(url).scrap()
    except Exception as err:
        print("ERR", url, str(err).splitlines()[0])


for url in ["https://www.mgeko.cc/manga/the-lords-coins-arent-decreasing/"]:
    try:
        mgeko.MgekoMangaSeriesScrapper(url).scrap()
    except Exception as err:
        print("ERR", url, str(err).splitlines()[0])
