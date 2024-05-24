import re
import json

import log
from app.utils import RequestUtils, JsonUtils
from config import MT_URL, Config


class MteamSpider(object):
    _indexerid = None
    _domain = None
    _name = ""
    _proxy = None
    _cookie = None
    _ua = None
    _size = 100
    _searchurl = "%s/api/torrent/search"
    _downloadurl = "%s/api/torrent/genDlToken"
    _pageurl = "%sdetail/%s"

    def __init__(self, indexer):
        if indexer:
            self._indexerid = indexer.id
            self._visit_domain = indexer.domain
            self._domain = MT_URL
            self._searchurl = self._searchurl % self._domain
            self._downloadurl = self._downloadurl % self._domain
            self._name = indexer.name
            if indexer.proxy:
                self._proxy = Config().get_proxies()
            self._cookie = indexer.cookie
            self._ua = indexer.ua
            if JsonUtils.is_valid_json(indexer.headers):
                self._headers = json.loads(indexer.headers)
            else:
                self._headers = {}
        self.init_config()

    def init_config(self):
        self._size = Config().get_config('pt').get('site_search_result_num') or 100

    def search(self, keyword="", page=0):
        params = {
            "mode": "normal",
            "categories": [],
            "visible": 1,
            "keyword": keyword,
            "pageNumber": int(page) + 1,
            "pageSize": self._size
            }

        params = json.dumps(params, separators=(',', ':'))
        self._headers.update({
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": f"{self._ua}"
            })
        res = RequestUtils(
            headers=self._headers,
            proxies=self._proxy,
            timeout=30
        ).post_res(url=self._searchurl, data=params)
        torrents = []
        if res and res.status_code == 200:
            results = res.json().get('data', {}).get("data") or []
            for result in results:
                imdbid = (re.findall(r'tt\d+', result.get('imdb')) or [''])[0]
                discount = result.get('status').get('discount')
                downloadvolumefactor = 0
                if discount == "FREE":
                    downloadvolumefactor = 0
                elif discount == "PERCENT_50":
                    downloadvolumefactor = 0.5
                elif discount == "PERCENT_70":
                    downloadvolumefactor = 0.3
                else:
                    downloadvolumefactor = 1.0
                torrent = {
                    'indexer': self._indexerid,
                    'title': result.get('name'),
                    'description': result.get('smallDescr'),
                    'enclosure': None,
                    'pubdate': result.get('createdDate'),
                    'size': result.get('size'),
                    'seeders': result.get('status').get('seeders'),
                    'peers': result.get('status').get('leechers'),
                    'grabs': result.get('status').get('timesCompleted'),
                    'downloadvolumefactor': downloadvolumefactor,
                    'uploadvolumefactor': 1.0,
                    'page_url': self._pageurl % (self._visit_domain, result.get('id')),
                    'imdbid': imdbid
                }
                torrents.append(torrent)
        elif res is not None:
            log.warn(f"【INDEXER】{self._name} 搜索失败，错误码：{res.status_code}")
            return True, []
        else:
            log.warn(f"【INDEXER】{self._name} 搜索失败，无法连接 {self._domain}")
            return True, []
        return False, torrents
