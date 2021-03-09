from datetime import datetime
import requests
import lxml.etree as le
from lxml.html import soupparser
from pathlib import Path
import path
from typing import List  # remove in python 3.9
import time
from .utils import clean_path, guess_extension, yyyymmdd_hhmm_format, yyyymmdd_hhmm_parse, json_dump
import logging
import os
import json
import re

logging.basicConfig(level=logging.INFO)


class Api:
    BASE_URL = "https://fantia.jp"
    API_URL = "https://fantia.jp/api/v1"

    def __init__(self, cookies) -> None:
        self.cookies = cookies
        session = requests.Session()
        session.cookies.update(cookies)
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_16_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36",
                "Accept-Encoding": "gzip, deflate, br",
            }
        )
        self.session = session
        self.cache = self.get_cache()

    def cache_path(self):
        return ".cache.json"

    def get_cache(self):
        cache = {}
        if os.path.exists(self.cache_path()):
            with open(self.cache_path()) as f:
                cache = json.load(f)
        return cache

    def save_cache(self):
        with open(self.cache_path(), 'w') as f:
            json_dump(self.cache, f)

    def get(self, url: str):
        return self.session.get(url)

    def check_user(self):
        if self.get(self.API_URL + "/me").status_code != 200:
            # TODO: graceful handling
            raise Exception("Cookie expired.")

    def sync(self, since: datetime = None):
        fanclubs = self.fanclub_list(False) + self.fanclub_list(True)
        l = len(fanclubs)
        for i, fanclub in enumerate(fanclubs):
            logging.info(f"Syncing {fanclub} ({i + 1} of {l})")
            # try:
            fanclub.sync(since)
            self.cache[fanclub.id] = fanclub.metadata
            # except Exception as e:
            #     logging.error(e)
            #     break
        self.save_cache()

    def fanclub_list(self, free: bool):
        logging.info("Fetching list of followed fanclubs")
        type = "free" if free else "not_free"
        html = self.get(f"https://fantia.jp/mypage/users/plans?type={type}").text
        html = le.HTML(html)

        fanclubs = []
        for fc in html.xpath(
            f"//a[@href='/mypage/users/plans?type={type}']/following::div[contains(@class, 'list-group')][1]/div[@class='list-group-item']"
        ):
            name, plan = fc.xpath(".//strong")[:2]
            id = name.xpath(f"./parent::a[1]/@href")[0].rsplit("/")[-1]
            # price = re.match(r'.+((?P<price>\d+)円/月)', '生きるプラン(300円/月)').group('price')
            fanclubs.append(Fanclub(self, id))
        return fanclubs

    def post_api_url(self, id):
        return f"{self.API_URL}/posts/{id}"

    def fanclub_api_url(self, id):
        return f"{self.API_URL}/fanclubs/{id}"

#
#  _____                _       _
# |  ___|_ _ _ __   ___| |_   _| |__
# | |_ / _` | '_ \ / __| | | | | '_ \
# |  _| (_| | | | | (__| | |_| | |_) |
# |_|  \__,_|_| |_|\___|_|\__,_|_.__/
#


class Fanclub(object):
    def __init__(self, api: Api, id) -> None:
        self.api = api
        metadata = api.cache.get(int(id))
        update = None
        old_price = 0
        if metadata:
            update = yyyymmdd_hhmm_parse(metadata["update"])
            old_price = metadata["price"]
        self.metadata_raw = api.get(api.fanclub_api_url(id)).json()["fanclub"]  # TODO: deal with name changes
        self.metadata = self.simplify_metadata()
        if self.metadata["price"] > old_price:
            update = None
        self.metadata["update"] = update

    def simplify_metadata(self):
        m = self.metadata_raw
        price = 0
        for plan in m["plans"]:
            if plan["order"]["status"] == "joined":
                price = plan["price"]
                break

        return {
            "id": int(m["id"]),
            "fanclub": m["name"],
            "username": m["user"]["name"],
            "user_id": m["user"]["id"],
            "price": price
        }

    def __getitem__(self, key):
        return self.metadata[key]

    def __str__(self):
        return f"{self.metadata['username']}({self.metadata['fanclub']})"

    def path(self):
        return clean_path(str(self))

    def metadata_path(self):
        return os.path.join(self.path(), ".metadata.json")

    def sync(self, since=datetime):
        # TODO: implement start point
        if not datetime:
            # lastest update
            pass
        for post in self.posts(self.metadata["update"]):
            post.sync()
            self.metadata["update"] = yyyymmdd_hhmm_format(post.date)

    # def save_metadata(self, timespan: (datetime, datetime)):
    #     d = self.path()
    #     Path(d).mkdir(exist_ok=True, parents=True)
    #     self.metadata["span"] = timespan
    #     with open(self.metadata_path(), 'w') as f:
    #         json_dump(self.metadata, f)

    def posts(self, since: datetime = None):
        posts = []
        i = 0
        logging.info(f"Fetching list of work of {self}")
        while True:
            i += 1
            logging.info(f"page {i}")
            url = f"https://fantia.jp/fanclubs/{self['id']}/posts?page={i}"
            html = self.api.get(url).text
            html = soupparser.fromstring(html)

            urls = html.xpath("//a[@class='link-block']/@href")
            print(url)
            print(urls)
            dates = [
                datetime.strptime(date, "%Y-%m-%d %H:%M")
                for date in html.xpath("//span[contains(@class, 'post-date')]//text()") if date != "更新"  # TODO: regex
            ]
            print(len(urls), len(dates))
            if since is None:
                posts += [
                    Post(self.api, urls[j].rsplit("/")[-1], dates[j]) for j in range(len(urls))
                ]
            else:
                for j, (date, url) in enumerate(zip(dates, urls)):
                    # TODO: possibly two updates in one minute?
                    print(j)
                    if date >= since:
                        posts.append(Post(self.api, urls[j].rsplit("/")[-1], dates[j]))
                    else:
                        return posts
            if len(html.xpath("//a[@rel='next']")) == 0:
                break
            time.sleep(1)
        return posts[::-1]


#
#  ____           _
# |  _ \ ___  ___| |_
# | |_) / _ \/ __| __|
# |  __/ (_) \__ \ |_
# |_|   \___/|___/\__|
#


class Post(object):
    def __init__(self, api: Api, id: str, date: datetime) -> None:
        self.api = api
        self.date = date

        api_url = api.post_api_url(id)
        r = api.get(api_url)
        if code := r.status_code != 200:
            raise Exception(f"Status code {code} when accessing {api_url}")

        self.metadata_raw = r.json()["post"]

        self.metadata = self.simplify_metadata()
        self.api.session.headers.update({"Referer": api_url})

    def __getitem__(self, key):
        return self.metadata[key]

    def sync(self):
        logging.info(f"Syncing {self['title']}")
        d = os.path.join(
            clean_path(str(self['fanclub'])),
            clean_path(
                self['date'].strftime("%Y-%m-%d") + '-' +
                self['title'] + '-' +
                str(self['id'])  # date and title can be identical
            )
        )
        Path(d).mkdir(exist_ok=True, parents=True)
        with path.Path(d):
            self.download_all()
        # if all contents require a higher subscription fee
        if len(os.listdir(d)) == 0:
            os.rmdir(d)

    def download(self, url: str, fn: str, mime: str = None):
        if not mime:
            mime = self.api.session.head(url).headers["Content-Type"]
        ext = guess_extension(mime, url)
        fn = clean_path(fn) + ext
        if not os.path.exists(fn):
            logging.info(f"Downloading {fn}")
            r = self.api.get(url)
            assert r.status_code == 200
            with open(fn, "wb") as f:
                f.write(r.content)
            time.sleep(0.5)

    def download_all(self, metadata: int = 1):
        # save metadata
        if metadata == 1:
            with open("metadata.json", 'w') as f:
                json_dump(self.metadata, f)
        elif metadata == 2:
            with open("metadata_raw.json", "w") as f:
                json_dump(self.metadata_raw, f)
        # download all available contents
        post_contents = self.metadata_raw["post_contents"]
        for i, block in enumerate(post_contents, start=1):
            if block["visible_status"] != "visible":
                # everything below is not visible
                break
            title = block["title"]
            description = block.get("comment")
            price = block["plan"] and block["plan"]["price"]
            category = block["category"]
            if category == "photo_gallery":
                for j, photo in enumerate(block["post_content_photos"], start=1):
                    photo_id = photo["id"]
                    self.download(photo["url"]["original"], f"{i}-{j}")
            elif category == "file":
                mime = block["content_type"]
                url = self.api.BASE_URL + block["download_uri"]
                self.download(url, str(i), mime)

    def simplify_metadata(self):
        m = self.metadata_raw
        f = m["fanclub"]
        return dict(
            id=m["id"],
            title=m["title"],
            date=self.date,
            description=m.get("comment"),
            fanclub=Fanclub(self.api, m["fanclub"]["id"]),
            rating=m["rating"],
            tags=[t["name"] for t in m["tags"]],
        )


# https://fantia.jp/api/v1/posts/625667 jpg, gif and mp4

