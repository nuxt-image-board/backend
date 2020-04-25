from base import BaseClient

cl = BaseClient()

endpoints = [
    "/news/list"
]

for e in endpoints:
    print(cl.get(e).json())