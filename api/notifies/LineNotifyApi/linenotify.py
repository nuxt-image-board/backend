import requests


class LineNotifyClient():
    baseUrl = "https://notify-api.line.me/api/"
    headers = {
        "Authorization": "Bearer <TOKEN>",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    def __init__(self, token=None):
        self.headers["Authorization"] = f"Bearer {token}"

    def setToken(self, token):
        self.headers["Authorization"] = f"Bearer {token}"

    def sendNotify(
        self,
        message,
        imageThumbnail=None,
        imageFullsize=None,
        notificationDisabled=False
    ):
        data = {
            "message": message,
            "imageThumbnail": imageThumbnail,
            "imageFullsize": imageFullsize,
            "notificationDisabled": notificationDisabled
        }
        resp = requests.post(
            self.baseUrl + "notify",
            headers=self.headers,
            data=data
        )
        if resp.status_code in [401, 400]:
            return Exception('Notify token error')
        return resp.json()

    def checkToken(self):
        resp = requests.get(
            self.baseUrl + "status",
            headers=self.headers
        )
        if resp.status_code in [401, 400]:
            return Exception('Notify token error')
        return resp.json()

    def revokeToken(self):
        resp = requests.post(
            self.baseUrl + "revoke",
            headers=self.headers
        )
        if resp.status_code in [401]:
            return Exception('Notify token error')
        return resp.json()


if __name__ == "__main__":
    cl = LineNotifyClient("TOKEN")
    print(cl.sendNotify('TEST', notificationDisabled=True))
