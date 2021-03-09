from .api import Api
from datetime import datetime

COOKIES = {
    "_session_id": "",
    "_ga": "",
    "_gid": "",
    "_gat_UA-76513494-1": "",
}

if __name__ == "__main__":
    api = Api(COOKIES)
    api.sync()
