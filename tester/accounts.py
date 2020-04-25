from base import BaseClient
import json
cl = BaseClient()

# アカウント作成
addEndpoint = "/accounts"
params = {
    "displayID":"kemu",
    "username":"けむ",
    "password":"***REMOVED***",
    "inviteCode":"PYONPYON"
}
resp = cl.post(addEndpoint, json=params).json()
print(resp)

# ログイン
'''
postEndpoint = "/accounts/login/form"
params = {
    "id":"omado",
    "password":"***REMOVED***",
}
resp = cl.post(postEndpoint, json=params).json()
print(resp)
apiKey = resp["apiKey"]

# 自分のアカウント情報
getEndpoint = "/accounts/me"
resp = cl.get(getEndpoint).json()
print(resp)
'''