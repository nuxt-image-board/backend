from base import BaseClient

cl = BaseClient()

endpoints = [
    "/catalog/artists",
    "/catalog/tags",
    "/catalog/characters",
]

for e in endpoints:
    print(cl.get(e).json())