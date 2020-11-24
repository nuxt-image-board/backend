from itsdangerous import JSONWebSignatureSerializer
from .upload_logger import UploadLogger
from .image_editor import UploadImageEditor
from ..notifies.notify_client import NotifyClient
import requests
import os


class UploadProcessorError(Exception):
    """アップロード処理中のエラー"""
    pass


class UploadProcessor():
    def __init__(self, conn, params):
        self.conn = conn
        self.params = params
        self.logger = UploadLogger(conn, params["userID"])
        self.editor = UploadImageEditor()

    def validateDuplication(self, origin_url):
        """出典重複を確認する"""
        resp = self.conn.get(
            """SELECT illustID FROM data_illust
            WHERE illustOriginUrl=%s
            AND illustOriginUrl <> 'https://gochiusa.com'""",
            (origin_url,)
        )
        if resp:
            self.logger.logDuplicatedImageError()
            raise UploadProcessorError("出典が重複しています")
        return True

    def getArtistId(self):
        """絵師IDを取得する"""
        artist_name = self.params["artist"].get("name", None)
        pixiv_id = self.params["artist"].get("pixivID", None)
        twitter_id = self.params["artist"].get("twitterID", None)
        # 既存の作者でなければ新規作成
        if not self.conn.has(
            "info_artist",
            "artistName=%s OR pixivID=%s OR twitterID=%s",
            (artist_name, pixiv_id, twitter_id)
        ):
            resp = self.conn.edit(
                """INSERT INTO info_artist
                (artistName,twitterID,pixivID,userID)
                VALUES (%s,%s,%s)""",
                (
                    artist_name,
                    pixiv_id,
                    twitter_id,
                    self.params.get("userID", "1")
                ),
                False
            )
            if not resp:
                self.conn.rollback()
                self.logger.logServerExplodedError()
                raise UploadProcessorError("新規作者ID作成に失敗しました")
        artist_id = self.conn.get(
            """SELECT artistID FROM info_artist
            WHERE artistName=%s OR pixivID=%s or twitterID=%s""",
            (artist_name, pixiv_id, twitter_id)
        )[0][0]
        return artist_id

    def registerIllustInfo(self):
        """イラスト情報を登録し、イラストIDを返す"""
        artist_id = self.getArtistId()
        illust_name = self.params.get("title", "無題")
        is_nsfw = self.params.get("nsfw", "0")
        is_nsfw = "1" if is_nsfw not in [0, "0", "False", "false"] else "0"
        resp = self.conn.edit(
            """INSERT INTO data_illust
            (artistID,illustName,illustDescription,illustPage,
            illustOriginUrl,illustOriginSite,userID,illustNsfw)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                artist_id,
                illust_name,
                self.params.get("caption", "コメントなし"),
                1,
                self.params.get("originUrl", "https://gochiusa.com"),
                self.params.get("originService", "不明"),
                self.params.get("userID", "1"),
                is_nsfw
            ),
            False
        )
        if not resp:
            self.conn.rollback()
            self.logger.logServerExplodedError()
            raise UploadProcessorError("新規イラストのDB登録に失敗しました")
        illust_id = self.conn.get(
            """SELECT illustID FROM data_illust
            WHERE illustName= %s ORDER BY illustID DESC""",
            (illust_name,)
        )[0][0]
        return illust_id

    def setImageSource(self, image_src):
        """画像パスから画像を読み込む"""
        self.editor.setImageSource(image_src)

    def getIllustExtension(self):
        """画像解像度を取得する"""
        extension = self.editor.getImageExtension()
        if extension in ["png", "jpg", "gif", "webp"]:
            return extension
        else:
            self.conn.rollback()
            self.logger.logServerExplodedError()
            raise UploadProcessorError("不正なファイルです")

    def createIllustImage(self, illust_id, static_dir):
        """登録したイラストの各種画像を作成する"""
        try:
            converts = {
                "thumb": [
                    self.editor.createThumb,
                    self.logger.logConvertedThumb
                ],
                "small": [
                    self.editor.createSmall,
                    self.logger.logConvertedSmall
                ],
                "large": [
                    self.editor.createLarge,
                    self.logger.logConvertedLarge
                ]
            }
            for c in converts.keys():
                dir = os.path.join(static_dir, c)
                img = converts[c][0]()
                for e in ["jpg", "webp"]:
                    img.save(
                        os.path.join(dir, f"{illust_id}.{e}"),
                        quality=80
                    )
                converts[c][1]()
        except Exception as e:
            print(e)
            for folder in ["orig", "thumb", "small", "large"]:
                dir = os.path.join(static_dir, folder)
                for extension in ["png", "jpg", "webp", "gif"]:
                    filePath = os.path.join(dir, f"{illust_id}.{extension}")
                    if os.path.exists(filePath):
                        os.remove(filePath)
            self.conn.rollback()
            self.logger.logServerExplodedError()
            raise UploadProcessorError("画像変換に失敗しました")
        return True

    def getIllustResolution(self):
        """画像パスから画像解像度を取得する"""
        width, height = self.editor.getImageSize()
        return width, height

    def getIllustHash(self):
        """画像パスから画像ハッシュを取得する"""
        hash = self.editor.getImageHash()
        return hash

    def registerIllustImageInfo(self, illust_id, file_bytes):
        """解像度/ハッシュ/拡張子/ファイルサイズを登録する"""
        width, height = self.getIllustResolution()
        hash = self.getIllustHash()
        extension = self.getIllustExtension()
        resp = self.conn.edit(
            """UPDATE data_illust
            SET illustExtension=%s, illustHash=%s, illustBytes=%s
            illustWidth = %s, illustHeight = %s
            WHERE illustID = %s""",
            (extension, hash, file_bytes, width, height, illust_id),
            False
        )
        if not resp:
            self.conn.rollback()
            self.logger.logServerExplodedError()
            raise UploadProcessorError("画像解像度の登録に失敗しました")
        return True

    def registerIllustTags(self, illust_id):
        """タグ/キャラ/グループ/システムタグをイラスト情報に登録する"""
        width, height = self.getIllustResolution()
        if not self.params["system"]:
            self.params["system"] = []
        if (width <= 720 and height <= 480)\
                or (height <= 720 and width <= 480):
            self.params["system"].append("SD")
        elif (width <= 1280 and height <= 720)\
                or (height <= 1280 and width <= 720):
            self.params["system"].append("HD")
        elif (width <= 1920 and height <= 1080)\
                or (height <= 1920 and width <= 1080):
            self.params["system"].append("FHD")
        elif (width <= 2560 and height <= 1440)\
                or (height <= 2560 and width <= 1440):
            self.params["system"].append("2K")
        else:
            self.params["system"].append("4K")
        tag_types = ["tag", "chara", "group", "system"]
        for tag_type_id, tag_type in enumerate(tag_types):
            if tag_type in self.params.keys():
                for tag_name in self.params[tag_type]:
                    if not self.conn.has(
                        "info_tag",
                        "tagName=%s",
                        (tag_name,)
                    ):
                        self.conn.edit(
                            """INSERT INTO info_tag
                            (userID,tagName,tagType,tagNsfw)
                            VALUES (%s, %s, %s, %s)""",
                            (
                                self.params.get("userID", "1"),
                                tag_name,
                                tag_type_id,
                                0
                            ),
                            False
                        )
                    tag_id = self.conn.get(
                        "SELECT tagID FROM info_tag WHERE tagName=%s",
                        (tag_name,)
                    )[0][0]
                    resp = self.conn.edit(
                        """INSERT INTO data_tag (illustID,tagID)
                        VALUES (%s, %s)""",
                        (illust_id, tag_id),
                        False
                    )
                    if not resp:
                        self.conn.rollback()
                        self.logger.logServerExplodedError()
                        raise UploadProcessorError(f"{tag_type}タグのDB登録に失敗しました")
        return True

    def registerIllustInfoCompleted(self, illust_id):
        """イラスト情報の登録完了を登録"""
        self.logger.logCompleted(illust_id)
        return True

    def sendIllustInfoNotify(self, illust_id):
        """イラスト情報の登録完了を通知"""
        notifier = NotifyClient(
            self.conn,
            self.params["onesignal"][0],
            self.params["onesignal"][1],
            self.params["telegram"]
        )
        notifier.sendArtNotify(illust_id)
        return True

    def givePyonToUser(self):
        """PYONを与える"""
        serializer = JSONWebSignatureSerializer(
            self.params["toymoney"]["salt"]
        )
        toymoney_key = self.conn.get(
            "SELECT userToyApiKey FROM data_user WHERE userID=%s",
            (self.params.get("userID", "1"),)
        )[0][0]
        toymoney_id = serializer.loads(toymoney_key)['id']
        endpoint = self.params["toymoney"]["endpoint"]
        token = self.params["toymoney"]["token"]
        amount = self.params["toymoney"]["amount"]
        resp = requests.post(
            f"{endpoint}/users/transactions/create",
            json={
                "target_user_id": toymoney_id,
                "amount": amount
            },
            headers={
                "Authorization": f"Bearer {token}"
            }
        )
        if resp.status_code != 200:
            self.logger.logServerExplodedError()
            raise UploadProcessorError(f"PYONの付与に失敗しました")
        return True
