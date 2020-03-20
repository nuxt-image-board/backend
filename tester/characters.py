from base import BaseClient
import json
cl = BaseClient()

addEndpoint = "/characters"
params = {
    "charaName":"hoge2",
    "charaDescription":"テストデータ"
}
resp = cl.post(addEndpoint, json=params).json()
print(resp)
charaID = resp["charaID"]

getEndpoint = f"/characters/{charaID}"
print(cl.get(getEndpoint).text)

putEndpoint = f"/characters/{charaID}"
params = {"charaName":"hoge3"}
print(cl.put(putEndpoint, json=params).text)

removeEndpoint = f"/characters/{charaID}"
print(cl.delete(removeEndpoint).text)