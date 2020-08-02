import requests
from .db import SQLHandler

conn = SQLHandler()
users = conn.get("SELECT userDisplayID FROM data_user WHERE userID > 3")

for u in users: 
    toyApiResp = requests.post(
        "http://127.0.0.1:7070/users/create",
        json={"name": u[0], "password": "***REMOVED***" + u[0]}
    ).json()["apiKey"]
    conn.edit("UPDATE data_user SET userToyApiKey = %s WHERE displayID = %s",(toyApiResp, u[0]))
print("OK")
