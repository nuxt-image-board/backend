from .TelegramApi.telegram import TelegramClient


class TelegramWrappedClient():
    GROUPS = {
        "ALL": -1001122896865,
        "香風智乃": -1001336130784,
        "保登心愛": -1001431654985,
        "桐間紗路": -1001478497127,
        "宇治松千夜": -1001344763569,
        "天々座理世": -1001272297947
    }

    def __init__(self, telegramToken):
        self.cl = TelegramClient(telegramToken)

    def sendNotify(self, tags, title, text, url):
        message = [
            text,
            "<Tags>",
            "\n".join(tags),
            "<Url>",
            url
        ]
        self.cl.sendPhoto(
            self.GROUPS["ALL"],
            caption=self.cl.escapeText("\n".join(message)),
            file_id_or_url=url
        )
        for t in self.GROUPS.keys():
            if t in tags:
                return self.cl.sendPhoto(
                    self.GROUPS[t],
                    caption=self.cl.escapeText("\n".join(message)),
                    file_id_or_url=url
                )


if __name__ == "__main__":
    import json
    with open('telegram_auth.json', 'r') as f:
        auth = json.loads(f.read())
    cl = TelegramWrappedClient(auth["token"])
    print(cl.sendNotify('chat_id', 'Text'))
