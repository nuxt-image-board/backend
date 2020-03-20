from base import BaseClient
import json
cl = BaseClient()

addEndpoint = "/artists"
params = {
    "artistName":"hoge2",
    "artistDescription":"テストデータ",
    "groupName":"サークル名",
    "pixivID":"hoge2",
    "twitterID":"hoge2",
    "mastodon":"example",
    "homepage":"example"
}
resp = cl.post(addEndpoint, json=params).json()
print(resp)
artistID = resp["artistID"]

getEndpoint = f"/artists/{artistID}"
print(cl.get(getEndpoint).text)


putEndpoint = f"/artists/{artistID}"
params = {"artistName":"hoge3"}
print(cl.put(putEndpoint, json=params).text)

removeEndpoint = f"/artists/{artistID}"
print(cl.delete(removeEndpoint).text)
