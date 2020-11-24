from .LineNotifyApi.linenotify import LineNotifyClient


class LineNotifyWrappedClient():
    def __init__(self, token=None):
        self.cl = LineNotifyClient(token)

    def sendNotify(self, tokens, title, text=None, url=None, image=None):
        message = "\n" + title
        resps = []
        if text:
            message += f"\n{text}"
        if url:
            message += f"\n{url}"
        for token in tokens:
            self.cl.setToken(token)
            resps.append(
                self.cl.sendNotify(
                    message=message,
                    imageThumbnail=image,
                    imageFullsize=image
                )
            )
        return resps


if __name__ == "__main__":
    import json
    with open('linenotify_tokens.json', 'r') as f:
        auth = json.loads(f.read())
    cl = LineNotifyWrappedClient()
    print(cl.sendNotify(auth["tokens"], 'title', 'caption',))
