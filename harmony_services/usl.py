import asyncio
import re
import httpx
import munch
import typing

from loguru import logger

_usl_cache: typing.Dict[str, typing.List[str]] = {}
_usl_wiki_index_url = "https://api.reddit.com/r/UniversalScammerList/wiki/banlist.json"
_usl_wiki_paginated_url = "https://api.reddit.com/r/UniversalScammerList/wiki/banlist/$_page_num.json"

_url_extract_regex = r'^\*\s+\[[^][]+]\((https?:\/\/[^()]+)\)$'
_page_number_extract_regex = r'^https?:\/\/www.reddit.com\/r\/universalscammerlist\/wiki\/banlist\/(\d+)$'
_data_extract_regex = r'^\*\s(\/u\/\S*)\s(#.*)$'

_usl_init_lock = asyncio.Lock()


async def update_usl():
    """
    Fetch the latest Universal Scammer List and update the cache.
    :return: Nothing.
    """
    async with httpx.AsyncClient() as http_client:
        # Fetch the USL wiki index.
        logger.info("Fetching USL wiki index...")
        usl_wiki_index = munch.munchify((await http_client.get(_usl_wiki_index_url)).json()).data.content_md
        page_urls = []

        # For each page link, extract the page number and convert it into an API URL
        for page in usl_wiki_index.splitlines():
            url_regex = re.search(_url_extract_regex, page)

            if not url_regex:
                continue

            page_urls.append(url_regex.group(1))

        logger.info(f"Got {len(page_urls)} pages to fetch data from.")

        if not _usl_cache:
            await _usl_init_lock.acquire()

        try:
            for page_url in page_urls:
                page_number = int(re.search(_page_number_extract_regex, page_url).group(1))
                page_api_url = _usl_wiki_paginated_url.replace("$_page_num", str(page_number))

                logger.info(f"Getting data from page {page_number}")

                usl_page = munch.munchify((await http_client.get(page_api_url)).json()).data.content_md

                for entry in usl_page.splitlines():
                    result = re.search(_data_extract_regex, entry)

                    username = result.group(1)
                    tags = result.group(2).strip().split(" ")

                    if username not in _usl_cache:
                        _usl_cache[username] = tags
        finally:
            _usl_init_lock.release()

        logger.info(f"Got a total of {len(_usl_cache)} valid results.")


async def lookup_usl(reddit_username: str) -> typing.Optional[typing.List[str]]:
    """
    Lookup a Reddit user in the Universal Scammer List.
    :param reddit_username: The Reddit username to look up.
    :return: The USL tags if a user is present in the USL, otherwise None.
    """
    if reddit_username.startswith("u/"):
        reddit_username = f"/{reddit_username}"
    else:
        reddit_username = f"/u/{reddit_username}"

    async with _usl_init_lock:
        return _usl_cache.get(reddit_username)
