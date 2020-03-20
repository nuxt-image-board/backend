import requests
import json

headers = {"Authorization":"Bearer ***REMOVED***"}
files = {
    "files": (
        "test.jpg",
        open("test.jpg","rb"),
        "image/jpeg"
    )
}

response = requests.post(
    'http://localhost:1337/upload',
    files=files,
    headers=headers
)
print(response.text)