import requests


class TelegramClient():
    baseUrl = "https://api.telegram.org/bot"
    precending = ['_', '*', '[', ']', '(', ')', '~', '`', '<', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

    def __init__(self, token=None):
        self.token = token

    def setToken(self, token):
        self.token = token

    def sendRequest(self, method, params=None):
        return requests.get(
            f"{self.baseUrl}{self.token}/{method}",
            params=params
        ).json()

    def getUpdates(self):
        return self.sendRequest("getUpdates")

    def escapeText(self, text):
        result = [t if t not in self.precending else "\\"+t for t in text]
        return "".join(result)

    def sendMessage(
        self,
        chat_id,
        text,
        parse_mode="MarkdownV2",
        disable_web_page_preview=False,
        disable_notification=False
    ):
        params = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
            "disable_notification": disable_notification
        }
        return self.sendRequest("sendMessage", params)

    def sendPhoto(
        self,
        chat_id,
        file_id_or_url,
        caption="",
        parse_mode="MarkdownV2",
        disable_notification=False
    ):
        params = {
            "chat_id": chat_id,
            "photo": file_id_or_url,
            "caption": caption,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification
        }
        return self.sendRequest("sendPhoto", params)


if __name__ == "__main__":
    cl = TelegramClient("TOKEN")
    print(cl.sendMessage('CHAT_ID', 'Hello World\\'))
