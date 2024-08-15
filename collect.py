# 2023 dec 12

import mangaclash, mgeko, urls

skip_chapter_in_json = True

#########################################################################
#                          Mangaclash                                   #
#########################################################################

for url in urls.mangaclash_urls:
    try:
        mangaclash.MangaClashMangaSeriesScrapper(
            url,
            skip_chapter_in_json=skip_chapter_in_json,
        ).scrap()
    except Exception as err:
        print("ERR", url, str(err).splitlines()[0])

#########################################################################
#                               mgeko                                   #
#########################################################################

for url in urls.mgeko_urls:
    try:
        mgeko.MgekoMangaSeriesScrapper(
            url,
            skip_chapter_in_json=skip_chapter_in_json,
        ).scrap()
    except Exception as err:
        print("ERR", url, str(err).splitlines()[0])
