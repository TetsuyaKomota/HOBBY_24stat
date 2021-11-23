import requests
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
import urllib
import time

# tmp/members.tsv にライバーの名前を書いて実行すると非公式wikiからchannel_id を取得してくる

url = "https://wikiwiki.jp/nijisanji/{member_name}"

s = requests.Session()

retries = Retry(total=5,
                backoff_factor=1,
                status_forcelist=[ 500, 502, 503, 504 ])

s.mount('https://', HTTPAdapter(max_retries=retries))
s.mount('http://', HTTPAdapter(max_retries=retries))

with open("tmp/members.tsv", "rt", encoding="utf-8") as f:
    for name in f:
        # res = requests.get(url.format(member_name=urllib.parse.quote(name.strip()))).text
        res = s.request('GET', url.format(member_name=urllib.parse.quote(name.strip())), timeout=2).text
        res = [l for l in res.split("<") if "youtube.com/channel" in l][0]
        res = res.split("channel/")[1].split('"')[0]

        print(f"  - {res} # {name.strip()}")
        time.sleep(0.1)
