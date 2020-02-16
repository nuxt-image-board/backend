import requests
import json

addr = "http://***REMOVED***:5000/arts"
filename = "hoge.jpg"

headers = {
    "Authorization": "Bearer ***REMOVED***"
}

params = {
    "title":"女の子チノちゃん",
    "originService":"Pixiv",
    "artist":{
        "name":"うみ猫"
    },
    "tag":["神絵師"]
}
file = open(filename,"rb")

files = {
    "file": file,
    "params": json.dumps(params)
}

resp = requests.post(addr,headers=headers,files=files).text
print(resp)