from base import BaseClient

cl = BaseClient()

endpoints = [
    "/navigations/characters",
    "/navigations/artists",
    "/navigations/tags",
]

for e in endpoints:
    print(cl.get(e).json())