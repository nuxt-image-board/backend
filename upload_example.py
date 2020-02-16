import requests
import json

addr = "http://***REMOVED***/arts"
filename = "hoge.png"

headers = {
    "Authorization": "Bearer ***REMOVED***"
}

params = {
    "title":"女の子チノちゃん4",
    "originService":"Pixiv",
    "artist":{
        "name":"うみ猫"
    }
}
file = open(filename,"rb")

files = {
    "file": file,
    "params": json.dumps(params)
}

resp = requests.post(addr,headers=headers,files=files).text
print(resp)