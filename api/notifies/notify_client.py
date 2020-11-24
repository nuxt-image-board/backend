from .linenotify_client import LineNotifyWrappedClient
from .onesignal_client import OneSignalWrappedClient
from .telegram_client import TelegramWrappedClient
import json

"""
targetType:
0 すべて
1 タグ
2 絵師
9 お知らせ(0:アプデ 1:誕生日 2:今日のおすすめ)

targetMethod:
0 OneSignal
1 LINE
2 Twitter
3 Telegram
"""


class NotifyClient():
    def __init__(
        self,
        conn,
        onesignal_appid,
        onesignal_token,
        telegram_token
    ):
        '''初期化時にクライアント作成'''
        self.conn = conn
        self.clients = [
            LineNotifyWrappedClient(),
            OneSignalWrappedClient(
                onesignal_appid,
                onesignal_token
            ),
            None,
            TelegramWrappedClient(
                telegram_token
            )
        ]
        self.clients[3].isTelegram = True

    def getOneSignalTarget(self, targetType, targetID):
        '''ターゲット手動取得'''
        oneSignalIds = self.conn.get(
            """SELECT userOneSignalID FROM data_user
            WHERE userID IN (
                SELECT userID FROM data_notify
                WHERE targetType=%s AND targetID=%s AND targetMethod=0
            ) AND userOneSignalID IS NOT NULL""",
            (targetType, targetID)
        )
        return oneSignalIds

    def getLineNotifyTarget(self, targetType, targetID):
        '''ターゲット手動取得'''
        lineNotifyTokens = self.conn.get(
            """SELECT userLineToken FROM data_user
            WHERE userID IN (
                SELECT userID FROM data_notify
                WHERE targetType=%s AND targetID=%s AND targetMethod=1
            ) AND userLineToken IS NOT NULL""",
            (targetType, targetID)
        )
        return lineNotifyTokens

    def getOneSignalTargetByData(self, tagIDs, artistID):
        '''まとめてとってくる場合'''
        oneSignalIds = self.conn.get(
            """SELECT userOneSignalID FROM data_user
            WHERE userID IN (
                SELECT userID FROM data_notify
                WHERE
                    (
                        targetType=0
                        OR (targetType=1 AND targetID IN %s)
                        OR (targetType=2 AND targetID=%s)
                    )
                    AND targetMethod=0
            ) AND uIserOneSignalD IS NOT NULL""",
            (tagIDs, artistID)
        )
        return oneSignalIds

    def getLineNotifyTargetByData(self, tagIDs, artistID):
        lineNotifyTokens = self.conn.get(
            """SELECT userLineToken FROM data_user
            WHERE userID IN (
                SELECT userID FROM data_notify
                WHERE
                    (
                        targetType=0
                        OR (targetType=1 AND targetID IN %s)
                        OR (targetType=2 AND targetID=%s)
                    )
                    AND targetMethod=1
            ) AND userLineToken IS NOT NULL""",
            (tagIDs, artistID)
        )
        return lineNotifyTokens

    def getArtNotifyTarget(self, tagIDs, artistID):
        # ここは公開すると最悪インジェクション仕放題なので注意
        # (リストを入れるにはプレースホルダを上手く使う必要あり)
        tagIDs = [str(int(t)) for t in tagIDs]
        inParams = "(" + ",".join([t for t in tagIDs]) + ")"
        datas = self.conn.get(
            f"""SELECT
                userOneSignalID, userLineToken, userTwitterID, targetMethod
            FROM
                data_notify
            NATURAL JOIN
                data_user
            WHERE
                (
                    targetType = 0 OR(
                        targetType = 1 AND targetID IN {inParams}
                    ) OR(
                        targetType = 2 AND targetID = %s
                    )
            )""",
            (artistID,)
        )
        oneSignalIds = [
            d[0].split(",")
            for d in datas
            if d[0] is not None and d[3] == 0
        ]
        oneSignalIds = [flatten for inner in oneSignalIds for flatten in inner]
        lineTokens = [
            d[1]
            for d in datas
            if d[1] is not None and d[3] == 1
        ]
        twitterIds = [
            d[2]
            for d in datas
            if d[2] is not None and d[3] == 2
        ]
        telegramIds = []
        return lineTokens, oneSignalIds, twitterIds, telegramIds

    def getTextNotifyTarget(self, targetID):
        datas = self.conn.get(
            """SELECT userLineToken, userOneSignalID,
            userTwitterID, targetMethod
            FROM data_user
            WHERE userID IN (
                SELECT userID FROM data_notify
                WHERE (targetType=9 AND targetID=%s)
            )""",
            (targetID,)
        )
        lineTokens = [d[0] for d in datas if d[0] is not None]
        oneSignalIds = [d[1].split(",") for d in datas if d[1] is not None]
        oneSignalIds = [flatten for inner in oneSignalIds for flatten in inner]
        twitterIds = [d[2] for d in datas if d[2] is not None]
        return lineTokens, oneSignalIds, twitterIds

    def sendArtNotify(self, illustID):
        # 存在しなければエラー
        if not self.conn.has("data_illust", "illustID=%s", (illustID,)):
            return Exception('The illust was not found')
        # 通知対象のタグ一覧取得
        targetTags = [
            r[0]
            for r in self.conn.get(
                "SELECT tagID FROM data_tag WHERE illustID=%s",
                (illustID,)
            )
        ]
        # 通知対象の作者ID取得
        targetArtist = self.conn.get(
            "SELECT artistID FROM data_illust WHERE illustID=%s",
            (illustID,)
        )[0][0]
        # 対象ユーザーをまとめて取り出し
        notifyTargets = self.getArtNotifyTarget(
            targetTags,
            targetArtist
        )
        # メッセージ作成
        title, description, artist, R18, extension = self.conn.get(
            """SELECT illustName, illustDescription, artistName, illustNsfw,
            illustExtension
            FROM data_illust INNER JOIN info_artist
            ON info_artist.artistID=data_illust.artistID WHERE illustID= %s""",
            (illustID,)
        )[0]
        text = "\n".join([
            f"<{title} {'(R18)' if R18 else ''}>",
            description[:100],
            artist,
            ""
        ])
        url = f"https://***REMOVED***/arts/{illustID}"
        # タグリスト生成
        tags = self.conn.get(
            f"""SELECT tagName FROM info_tag NATURAL JOIN
                (SELECT tagID FROM data_tag WHERE illustID={illustID}) AS T2"""
        )
        # 通知を送る
        for cl, data in zip(self.clients, notifyTargets):
            if cl is not None and not hasattr(cl, "isTelegram"):
                cl.sendNotify(data, "新しいイラストが投稿されました!", text, url)
            elif cl is not None:
                tags = [t[0] for t in tags]
                cl.sendNotify(
                    tags,
                    title,
                    text,
                    f"https://***REMOVED***/illusts/orig/{illustID}.{extension}"
                )
        return True

    def sendMessageNotify(
        self,
        targetID,
        title,
        text=None,
        url=None,
        image=None
    ):
        # テキストで通知を送る (ID0:アプデ ID1:誕生日 ID2:おすすめ)
        notifyTargets = self.getTextNotifyTarget(
            targetID
        )
        # 通知を送る
        for cl, data in zip(self.clients, notifyTargets):
            # print(data)
            if cl is not None:
                cl.sendNotify(data, title, text, url, image)
        return True


if __name__ == "__main__":
    # cl = NotifyClient(SQLHandler())
    # print(cl.sendArtNotify(1))
    pass
