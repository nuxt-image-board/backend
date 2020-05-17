import requests

'''
権限9
Bearer ***REMOVED***

権限5
***REMOVED***

'''


class BaseClient():
    def __init__(self, address="http://localhost:5000", token="***REMOVED***"):
        self.address = address
        self.headers = {
            "Authorization": "Bearer " + token,
            "ContentType": "application/json"
        }

    def post(self, endpoint, params=None, data=None, json=None, files=None):
        return requests.post(
            self.address + endpoint,
            params=params,
            json=json,
            headers=self.headers,
            files=files
        )

    def get(self, endpoint, params=None, data=None, json=None, files=None):
        return requests.get(
            self.address + endpoint,
            params=params,
            data=data,
            json=json,
            headers=self.headers
        )

    def put(self, endpoint, params=None, data=None, json=None, files=None):
        return requests.put(
            self.address + endpoint,
            params=params,
            data=data,
            json=json,
            headers=self.headers
        )

    def delete(self, endpoint, params=None, data=None, json=None, files=None):
        return requests.delete(
            self.address + endpoint,
            params=params,
            data=data,
            json=json,
            headers=self.headers
        )
