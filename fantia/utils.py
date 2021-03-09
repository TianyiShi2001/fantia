from urllib.parse import urlparse
import os
import mimetypes
import re
from datetime import datetime
import json


INVALID_PATH_CHARACTERS = re.compile(r"[<>\"\?\\\/\*:|]")


def guess_extension(mimetype, url):
    """
    Guess the file extension from the mimetype or force a specific extension for certain mimetypes.
    If the mimetype returns no found extension, guess based on the download URL.
    """
    return (
        mimetypes.guess_extension(mimetype)
        or os.path.splitext(urlparse(url).path)[1]
        or ".unknown"
    )


def clean_path(value, replace=" "):
    """Remove potentially illegal characters from a path."""
    cleaned = INVALID_PATH_CHARACTERS.sub(replace, value)
    return re.sub(r"[\s.]+$", "", cleaned)


def yyyymmdd_hhmm_format(date: datetime) -> str:
    return date.strftime("%Y-%m-%d %H:%M")


def yyyymmdd_hhmm_parse(date: str) -> datetime:
    return datetime.strptime("%Y-%m-%d %H:%M", date)


def json_converter(o):
    if isinstance(o, datetime):
        return yyyymmdd_hhmm_format(o)
    return o.__str__()


def json_dump(o, f):
    json.dump(o, f, default=json_converter, ensure_ascii=False)