from base import BaseClient

cl = BaseClient()

# 画像検索
with open("79.jpg","rb") as f:
    files = {"file": ("79.jpg", f.read(), "image/jpeg")}
scrapeEndpoint = "/search/image/ascii2d"
resp = cl.post(scrapeEndpoint, files=files).json()
print(resp)
