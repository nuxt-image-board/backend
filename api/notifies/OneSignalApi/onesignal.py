import requests


class OneSignalClient():
    baseUrl = "https://onesignal.com/api/v1/"
    headers = {
        "Authorization": "Basic "
    }
    params = {
        "app_id": "",
        "headings": {
            "en": "",
            "ja": ""
        },
        "contents": {
            "en": "",
            "ja": ""
        },
        "include_player_ids": []
    }

    def __init__(self, appId, apiKey):
        self.headers["Authorization"] = "Basic " + apiKey
        self.params["app_id"] = appId

    def sendNotify(self, title, text, playerIds, url=None, image=None, buttons=None):
        endpoint = "notifications"
        # タイトル
        self.params["headings"]["en"] = title
        self.params["headings"]["ja"] = title
        # 内容
        self.params["contents"]["en"] = text
        self.params["contents"]["ja"] = text
        self.params["include_player_ids"] = playerIds
        if url:
            self.params["url"] = url
        if image:
            # iOS用
            self.params["ios_attachments"] = {"image1": image}
            # Android用
            self.params["big_picture"] = image
            # Chrome Web用
            self.params["chrome_web_image"] = image
            # Chrome App用
            self.params["chrome_big_picture"] = image
        resp = requests.post(
            self.baseUrl + endpoint,
            json=self.params,
            headers=self.headers
        )
        return resp.text


if __name__ == "__main__":
    import json
    with open('onesignal_auth.json', 'r') as f:
        data = json.loads(f.read())
        KEY = data['token']
        APP_ID = data['appId']
    USER = "INPUT_USER_ID"
    cl = OneSignalClient(APP_ID, KEY)
    print(
        cl.sendNotify(
            "新着イラスト通知",
            "〇〇さんの新着イラストが投稿されました",
            [USER],
            url="https://gochiusa.com",
            image="IMAGE_URL"
        )
    )
