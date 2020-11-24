from .upload_processor import UploadProcessor, UploadProcessorError
from ..db import SQLHandler
import shutil
import os

'''
REQ
{
    "title":"Test",
    "caption":"テストデータ",
    "originUrl": "元URL",
    "originService": "元サービス名",
    "imageUrl": "画像の元URL",
    //どれか1つが存在するかつあってればOK
    "artist":{
        "twitterID":"適当でも",
        "pixivID":"適当でも",
        "name":"適当でも"
    },
    "tag":["","",""],
    "chara": ["","",""],
    "nsfw": 0
}
'''


def registerIllust(params):
    # インスタンス作成
    conn = SQLHandler(
        params["db"]["name"],
        params["db"]["host"],
        params["db"]["port"],
        params["db"]["user"],
        params["db"]["pass"]
    )
    processor = UploadProcessor(conn, params)
    try:
        # 出典アドレス
        origin_url = params["imageUrl"]
        # 出典重複検証
        processor.validateDuplication(origin_url)
        # 仮の情報登録をしてイラストIDを得る
        illust_id = processor.registerIllustInfo()
        # 画像保存先フォルダ
        static_dir = "static/illusts/"
        orig_path = os.path.join(
            static_dir,
            "orig",
            f"{illust_id}.raw"
        )
        real_orig_path = orig_path
        # 何枚目の画像を保存するかはURLパラメータで見る
        if "?" in origin_url and params["own_address"] not in origin_url:
            origin_url = origin_url[:origin_url.find("?")]
        # ローカルから取る場合
        shutil.move(
            origin_url[origin_url.find("/static/temp/")+1:],
            orig_path
        )
        # 保存した画像を入力
        processor.setImageSource(orig_path)
        # 正しい拡張子を取得(不正なデータならここでエラーが返る)
        extension = processor.getIllustExtension()
        real_orig_path = orig_path.replace("raw", extension)
        shutil.move(
            orig_path,
            real_orig_path
        )
        # 解像度/ハッシュ/拡張子/ファイルサイズを登録
        filesize = os.path.getsize(real_orig_path)
        processor.registerIllustImageInfo(illust_id, filesize)
        # イラストタグを登録
        processor.registerIllustTags(illust_id)
        # 変換完了を記録
        processor.registerIllustInfoCompleted(illust_id)
        # 通知を送る
        processor.sendIllustInfoNotify(illust_id)
        # PYONを付与
        processor.givePyonToUser()
    except UploadProcessorError:
        if os.path.exists(orig_path):
            os.remove(orig_path)
        if os.path.exists(real_orig_path):
            os.remove(real_orig_path)
        return False
    else:
        return True
    finally:
        conn.close()


if __name__ == "__main__":
    params = {
        "title": "Test",
        "caption": "テストデータ",
        "originUrl": "元URL",
        "originService": "元サービス名",
        "imageUrl": "画像の元URL",
        "artist": {
            "name": "適当でも"
        },
        "tag": ["テスト"],
        "nsfw": 0
    }
    from dotenv import load_dotenv
    load_dotenv(verbose=True, override=True)
    params["db"] = {
        "name": os.environ.get("DB_NAME"),
        "host": os.environ.get("DB_HOST"),
        "port": os.environ.get("DB_PORT"),
        "user": os.environ.get("DB_USER"),
        "pass": os.environ.get("DB_PASS")
    }
    params["toymoney"] = {
        "salt": os.environ.get("SALT_TOYMONEY"),
        "endpoint": os.environ.get("TOYMONEY_ENDPOINT"),
        "token": os.environ.get("TOYMONEY_TOKEN"),
        "amount": 2
    }
    registerIllust(params)
