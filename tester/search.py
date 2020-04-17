from base import BaseClient
import json
cl = BaseClient()

params = {
    "id":"1",
    "sort":"d",
    "order": "d",
    "page": "1",
    "keyword": "魔法"
}
getEndpoints = [
    "/search/tag",
    "/search/artist",
    "/search/character",
    "/search/keyword",
    "/search/all",
]
for e in getEndpoints:
    try:
        print(cl.get(e,params=params).json())
    except:
        pass
        
# 画像検索 
with open("1.png","rb") as f:
    files = {"file": ("1.png", f.read(), "image/png")}
scrapeEndpoint = "/search/image"
resp = cl.post(scrapeEndpoint, files=files).json()
print(resp)

scrapeEndpoint = "/search/image/saucenao"
resp = cl.post(scrapeEndpoint, files=files).json()
print(resp)