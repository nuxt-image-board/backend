from base import BaseClient
import json
cl = BaseClient()

addEndpoint = "/tags"
params = {
    "tagName":"TestTag7",
    "tagDescription":"TestTag7",
    "nsfw": "1"
}
resp = cl.post(addEndpoint, json=params).json()
print(resp)
tagID = resp["tagID"]

getEndpoint = f"/tags/{tagID}"
print(cl.get(getEndpoint).text)

putEndpoint = f"/tags/{tagID}"
params = {"tagName":"TestTag10"}
print(cl.put(putEndpoint, json=params).text)


removeEndpoint = f"/tags/{tagID}"
print(cl.delete(removeEndpoint).text)
