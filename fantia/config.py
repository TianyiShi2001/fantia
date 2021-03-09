import os
import yaml

SLEEP = 0.5
CACHE_FILE = ".cache.json"
AUTHOR_FORMAT = "%C (%N)"
DATE_FORMAT = "%y-%m-%d"

CONFIG_FILE = "config.yml"
if os.path.exists(CONFIG_FILE):
    c = yaml.load(CONFIG_FILE)
    SLEEP = c.get("sleep") or SLEEP
    CACHE_FILE = c.get("cache_file") or CACHE_FILE
    AUTHOR_FORMAT = c.get("author_format") or AUTHOR_FORMAT
    DATE_FORMAT = c.get("date_format") or DATE_FORMAT

