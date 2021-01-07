from flask import Blueprint, g, request, jsonify, escape, current_app
from ..extensions import (
    auth, limiter, handleApiPermission, record, cache
)
from ..worker.worker import registerIllust
from datetime import datetime
from redis import Redis
from rq import Queue
from hurry.filesize import size
import tempfile
import json
import shutil
import traceback
import requests
from os import environ
from dotenv import load_dotenv

# .env読み込み
load_dotenv(verbose=True, override=True)
OWN_ADDRESS = environ.get("API_OWN_ADDRESS")
REDIS_HOST = environ.get("REDIS_HOST")
REDIS_PORT = int(environ.get("PORT_REDIS"))
REDIS_DB = int(environ.get("REDIS_DB"))
DB_NAME = environ.get("DB_NAME")
DB_HOST = environ.get("DB_HOST")
DB_PORT = environ.get("PORT_DB")
DB_USER = environ.get("DB_USER")
DB_PASS = environ.get("DB_PASS")
TOYMONEY_SALT = environ.get('SALT_TOYMONEY')
TOYMONEY_ENDPOINT = environ.get('TOYMONEY_ENDPOINT')
TOYMONEY_TOKEN = environ.get('TOYMONEY_TOKEN')
TOYMONEY_AMOUNT = 2


arts_api = Blueprint('arts_api', __name__)

#
# イラストの投稿関連
#


@arts_api.route('/', methods=["POST"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def createArt():
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
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
    # 最低限のパラメータ確認
    params = request.get_json()
    if not params:
        return jsonify(status=400, message='bad request: not json')
    # パラメータ確認
    requiredParams = set(("title", "originService"))
    validParams = [
        "title", "caption", "imageUrl",
        "originUrl", "originService",
        "artist", "tag", "chara",
        "system", "group", "nsfw"
    ]
    # 必須パラメータ確認
    params = {p: params[p] for p in params.keys() if p in validParams}
    if not requiredParams.issubset(params.keys()):
        return jsonify(status=400, message='bad request: not enough')
    # 作者パラメータ確認
    if "name" not in params["artist"]\
            and "twitterID" not in params["artist"]\
            and "pixivID" not in params["artist"]:
        return jsonify(status=400, message="Artist paramators are invalid.")
    # 画像アドレスパラメータ確認
    supported_address = [
        f"{OWN_ADDRESS}/static/temp/"
    ]
    if not any([
        params["imageUrl"].startswith(a)
        for a in supported_address
    ]):
        return jsonify(status=400, message='bad request: not valid url')
    # バリデーションする
    params["title"] = g.validate(
        params.get("title", "無題"),
        lengthMax=50,
        escape=False
    )
    params["caption"] = g.validate(
        params.get("caption", "コメントなし"),
        lengthMax=300
    )
    params["originService"] = g.validate(
        params.get("originService", "不明"),
        lengthMax=20
    )
    params["userID"] = g.userID
    params["db"] = {
        "name": DB_NAME,
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "pass": DB_PASS
    }
    params["toymoney"] = {
        "salt": TOYMONEY_SALT,
        "endpoint": TOYMONEY_ENDPOINT,
        "token": TOYMONEY_TOKEN,
        "amount": 2
    }
    params["own_address"] = OWN_ADDRESS
    # Workerにパラメータを投げる
    if not current_app.debug:
        q = Queue(
            connection=Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB),
            job_timeout=120,
            description=f'UploadProcessor (Issued by User{g.userID})'
        )
        q.enqueue(registerIllust, params)
        record(g.userID, "addArt", param1=-1)
    return jsonify(status=202, message="Accepted")


@arts_api.route('/<int:illustID>', methods=["DELETE"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def destroyArt(illustID):
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    # TODO: 管理ユーザー: ファイルから削除する
    # 通常ユーザー: 非表示状態にする
    resp = g.db.edit(
        "UPDATE data_illust SET illustStatus=1 WHERE illustID=%s",
        (illustID,)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed")
    return jsonify(status=200, message="success")


@arts_api.route('/<int:illustID>', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=5)
def getArt(illustID):
    # TODO: 置き換え情報の取得と応答
    artData = g.db.get(
        """SELECT
            data_illust.illustID,
            illustName,
            illustDescription,
            illustDate,
            illustPage,
            illustLike,
            illustView,
            illustOriginUrl,
            illustOriginSite,
            illustNsfw,
            illustHash,
            illustExtension,
            data_illust.artistID,
            artistName,
            data_illust.userID,
            userName,
            illustStatus,
            illustWidth,
            illustHeight,
            illustBytes,
            illustStarYellow,
            illustStarGreen,
            illustStarRed,
            illustStarBlue
        FROM
            data_illust
        INNER JOIN
            info_artist
        ON
            data_illust.artistID = info_artist.artistID
        INNER JOIN
            data_user
        ON
            data_illust.userID = data_user.userID
        WHERE
            illustID = %s""",
        (illustID,)
    )
    if not len(artData):
        return jsonify(status=404, message="The art data was not found.")
    if artData[0][16] == 2:
        return jsonify(status=404, message="The art data was not found.")
    artData = artData[0]
    # タグ情報取得
    tagDataList = g.db.get(
        """SELECT tagID,tagName,tagNsfw,tagType FROM data_tag
        NATURAL JOIN info_tag WHERE illustID = %s""",
        (illustID,)
    )
    # リストを分ける
    tagData = [[t[0], t[1], t[2]] for t in tagDataList if t[3] == 0]
    charaData = [[t[0], t[1]] for t in tagDataList if t[3] == 1]
    groupData = [[t[0], t[1]] for t in tagDataList if t[3] == 2]
    systemData = [[t[0], t[1]] for t in tagDataList if t[3] == 3]
    # マイリストカウント取得
    mylistCount = g.db.get(
        "SELECT COUNT(illustID) FROM data_mylist WHERE illustID = %s",
        (illustID,)
    )
    mylistCount = mylistCount[0][0] if mylistCount else 0
    # マイリスト済みか取得
    isMylisted = g.db.has(
        "data_mylist",
        """mylistID IN (SELECT mylistID FROM info_mylist WHERE userID=%s)
        AND illustID = %s""",
        (g.userID, illustID)
    )
    replacedData = g.db.get(
        """SELECT
            illustID, illustName, illustDescription,
            illustDate, illustOriginSite, illustOriginUrl,
            illustWidth, illustHeight, illustBytes
        FROM
            data_illust
        WHERE
            illustID IN(
            SELECT
                illustLowerID
            FROM
                data_replace
            WHERE
                illustGreaterID=%s) """,
        (illustID,)
    )
    return jsonify(status=200, data={
        "illustID": artData[0],
        "title": artData[1],
        "caption": artData[2],
        "date": artData[3].strftime('%Y-%m-%d %H:%M:%S'),
        "pages": artData[4],
        "like": artData[5],
        "view": artData[6],
        "mylist": mylistCount,
        "mylisted": isMylisted,
        "originUrl": artData[7],
        "originService": artData[8],
        "nsfw": artData[9],
        "hash": artData[10],
        "extension": artData[11],
        "artist": {
            "id": artData[12],
            "name": artData[13]
        },
        "user": {
            "id": artData[14],
            "name": artData[15]
        },
        "status": artData[16],
        "width": artData[17],
        "height": artData[18],
        "filesize": size(artData[19]),
        "tag": tagData,
        "chara": charaData,
        "group": groupData,
        "system": systemData,
        "replace": [{
            "illustID": r[0],
            "title": r[1],
            "caption": r[2],
            "date": r[3].strftime('%Y-%m-%d %H:%M:%S'),
            "originService": r[4],
            "originUrl": r[5],
            "width": r[6],
            "height": r[7],
            "filesize": r[8]
        } for r in replacedData],
        "star": [
            artData[20],
            artData[21],
            artData[22],
            artData[23]
        ]
    })


@arts_api.route('/<int:illustID>', methods=["PUT"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def editArt(illustID):
    # TODO: 権限確認処理の欠如をどうにかする
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    if not params:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    # まず一旦タグを全部破壊
    resp = g.db.edit(
        "DELETE FROM data_tag WHERE illustID = %s",
        (illustID,)
    )
    # タグとキャラの追加
    for i, k in enumerate(["tag", "chara", "group", "system"]):
        if k in params.keys():
            for t in params[k]:
                # 存在しないタグは作成
                if not g.db.has("info_tag", "tagName=%s", (t,)):
                    g.db.edit(
                        """INSERT INTO info_tag
                        (userID,tagName,tagType,tagNsfw)
                        VALUES (%s,%s,%s,0)""",
                        (g.userID, t, i),
                        False
                    )
                tagID = g.db.get(
                    "SELECT tagID FROM info_tag WHERE tagName=%s",
                    (t,)
                )[0][0]
                # タグIDのデータ挿入
                resp = g.db.edit(
                    f"""INSERT INTO data_tag (illustID,tagID)
                    VALUES ({illustID}, {tagID})""",
                    autoCommit=False
                )
                # 爆発したら 死亡を返す
                if not resp:
                    g.db.rollback()
                    return jsonify(status=500, message="Server bombed.")
    # 作者名の編集
    if "artist" in params.keys():
        # 同じ名前があるなら既存の作者のIDに変更する
        if g.db.has(
            "info_artist",
            "artistName=%s",
            (params["artist"]["name"],)
        ):
            artistID = g.db.get(
                "SELECT artistID FROM info_artist WHERE artistName=%s",
                (params["artist"]["name"],)
            )[0][0]
            resp = g.db.edit(
                "UPDATE data_illust SET artistID = %s WHERE illustID=%s",
                (artistID, illustID),
                autoCommit=False
            )
            # 古い方の作者IDはとりあえず放置しておく(GCで消し去る?)
            if not resp:
                g.db.rollback()
                return jsonify(status=500, message="Server bombed.")
        # そうでなければ今の作者の名前を変更する
        else:
            artistID = g.db.get(
                "SELECT artistID FROM data_illust WHERE illustID=%s",
                (illustID,)
            )[0][0]
            resp = g.db.edit(
                "UPDATE info_artist SET artistName = %s WHERE artistID=%s",
                (params["artist"]["name"], artistID)
            )
            if not resp:
                g.db.rollback()
                return jsonify(status=500, message="Server bombed.")
    validParams = {
        "artistId": "artistID",
        "title": "illustName",
        "caption": "illustDescription",
        "date": "illustDate",
        "page": "illustPage",
        "tag": "tag",
        "chara": "chara",
        "originUrl": "illustOriginUrl",
        "originService": "illustOriginSite",
        "illustLikeCount": "illustLike",
        "illustOwnerId": "userID",
        "nsfw": "illustNsfw",
        "status": "illustStatus"
    }
    params = {
        validParams[p]: params[p]
        for p in params.keys() if p in validParams.keys()
    }
    if not params:
        g.db.rollback()
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    for extra in ['tag', 'chara']:
        if extra in params.keys():
            del params[extra]
    if "artistID" in params.keys():
        isExist = g.db.has("info_artist", "artistID=%s", (params[p],))
        if not isExist:
            g.db.rollback()
            return jsonify(
                status=400,
                message="Specified artist was not found."
            )
    for p in params.keys():
        resp = g.db.edit(
            f"UPDATE data_illust SET {p}=%s WHERE illustID=%s",
            (params[p], illustID,),
            False
        )
        if not resp:
            g.db.rollback()
            return jsonify(status=500, message="Server bombed.")
    g.db.commit()
    return jsonify(status=200, message="Update succeed.")


@arts_api.route(
    '/<int:illustLowerID>/replace',
    methods=["PUT"],
    strict_slashes=False
)
@auth.login_required
@limiter.limit(handleApiPermission)
def replaceArt(illustLowerID):
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    if not params:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    if "status" not in params or "illustID" not in params:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    # 置き換えられるIDが illustLowerID
    # 置き換え(よりよい方)が illustGreaterID
    illustGreaterID = int(params["illustID"])
    # 処理の確認 (置き換え後にどうなるかを返す)
    if params["status"] != 1:
        resp = {}
        for id in [illustLowerID, illustGreaterID]:
            artData = g.db.get(
                """SELECT
                    data_illust.illustID,
                    illustName,
                    illustDescription,
                    illustDate,
                    illustPage,
                    illustLike,
                    illustOriginUrl,
                    illustOriginSite,
                    illustNsfw,
                    illustHash,
                    illustExtension,
                    data_illust.artistID,
                    artistName,
                    data_illust.userID,
                    userName,
                    illustStatus,
                    illustWidth,
                    illustHeight,
                    illustBytes,
                    illustStarYellow,
                    illustStarGreen,
                    illustStarRed,
                    illustStarBlue
                FROM
                    data_illust
                INNER JOIN
                    info_artist
                ON
                    data_illust.artistID = info_artist.artistID
                INNER JOIN
                    data_user
                ON
                    data_illust.userID = data_user.userID
                WHERE
                    illustID = %s""",
                (id,)
            )
            if not len(artData):
                return jsonify(
                    status=404,
                    message="The art data was not found."
                )
            artData = artData[0]
            resp["to" if id == illustGreaterID else "from"] = {
                "illustID": artData[0],
                "title": artData[1],
                "caption": artData[2],
                "date": artData[3].strftime('%Y-%m-%d %H:%M:%S'),
                "pages": artData[4],
                "like": artData[5],
                "originUrl": artData[6],
                "originService": artData[7],
                "nsfw": artData[8],
                "hash": artData[9],
                "extension": artData[10],
                "artist": {
                    "id": artData[11],
                    "name": artData[12]
                },
                "user": {
                    "id": artData[13],
                    "name": artData[14]
                },
                "status": artData[15],
                "width": artData[16],
                "height": artData[17],
                "filesize": size(artData[18]),
                "star": [
                    artData[19],
                    artData[20],
                    artData[21],
                    artData[22]
                ]
            }
        return jsonify(status=200, message="ok", data=resp)
    # 実際に処理する
    # 古いイラストを非表示にする
    resp = g.db.edit(
        "UPDATE data_illust SET illustStatus=1 WHERE illustID = %s",
        (illustLowerID,)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    # 古いイラストのいいねを読み出す
    oldLikeCount = g.db.get(
        "SELECT illustLike FROM data_illust WHERE illustID = %s",
        (illustLowerID,)
    )
    if not oldLikeCount:
        return jsonify(status=500, message="Server bombed.")
    oldLikeCount = oldLikeCount[0][0]
    # 新しい方にいいねを足す
    resp = g.db.edit(
        "UPDATE data_illust SET illustLike=illustLike+%s WHERE illustID = %s",
        (oldLikeCount, illustGreaterID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    # 古い方のイラストのタグを読み出す
    oldTags = g.db.get(
        "SELECT tagID FROM data_tag WHERE illustID = %s",
        (illustLowerID,)
    )
    if not oldTags:
        return jsonify(status=500, message="Server bombed.")
    oldTags = [t[0] for t in oldTags]
    # 新しい方のタグを統合する
    # エラーが発生しても握りつぶされるのでスルー
    for t in oldTags:
        g.db.edit(
            "INSERT INTO data_tag (illustID,tagID) VALUES (%s, %s)",
            (illustGreaterID, t)
        )
    # 置き換え情報を挿入する(どちらがどちらを置き換えたかはカラムでわかる)
    resp = g.db.edit(
        "INSERT INTO data_replace "
        + "(illustGreaterID,illustLowerID) VALUES (%s,%s)",
        (illustGreaterID, illustLowerID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Replace succeed")

#
# イラストのタグ関連
#   createArtTag は createArtと同時にされるので無い


@arts_api.route(
    '/<int:illustID>/tags',
    methods=["DELETE"],
    strict_slashes=False
)
@auth.login_required
@limiter.limit(handleApiPermission)
def deleteArtTag(illustID):
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    if not params:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    try:
        tagID = int(params.get("tagID"))
    except:
        return jsonify(
            status=400,
            message="tagID is invalid, or not specified."
        )
    isExist = g.db.has(
        "data_tag",
        "illustID=%s AND tagID=%s",
        (illustID, tagID,)
    )
    if not isExist:
        return jsonify(
            status=400,
            message="The tag is not registered to the art."
        )
    resp = g.db.edit(
        "DELETE FROM `data_tag` "
        + "WHERE illustID = %s AND tagID = %s",
        (illustID, tagID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Remove succeed.")


@arts_api.route('/<int:illustID>/tags', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def getArtTag(illustID):
    '''指定されたイラスト付属のタグ一覧を、フルデータとして取得する'''
    resp = g.db.get(
        f"""SELECT * FROM info_tag
        NATURAL JOIN
        (SELECT tagID FROM data_tag WHERE illustID=%s)
        WHERE tagType=0""",
        (illustID,)
    )
    if not len(resp):
        return jsonify(status=404, message="The art don't have any tag.")
    return jsonify(
        status=200,
        message="found",
        data=[{
            "tagID": r[0],
            "name": r[1],
            "caption": r[2],
            "nsfw": r[3]
        } for r in resp]
    )


@arts_api.route('/<int:illustID>/tags', methods=["PUT"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def addArtTag(illustID):
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    if not params:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    try:
        tagID = int(params.get("tagID"))
        isExist = g.db.has("info_tag", "tagID=%s", (tagID,))
        if tagID < 0 or not isExist:
            raise ValueError()
    except:
        return jsonify(
            status=400,
            message="tagID is invalid, or not specified."
        )
    isExist = g.db.has(
        "data_tag", "illustID=%s AND tagID=%s", (illustID, tagID,))
    if isExist:
        return jsonify(
            status=400,
            message="The tag is already registered to the art."
        )
    resp = g.db.edit(
        "INSERT INTO `data_tag` (`illustID`,`tagID`) "
        + "VALUES (%s,%s);",
        (illustID, tagID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Add succeed.")

#
# イラストのキャラ関連
#   createArtCharacater は createArtと同時にされるので無い


@arts_api.route(
    '/<int:illustID>/characters',
    methods=["DELETE"],
    strict_slashes=False
)
@auth.login_required
@limiter.limit(handleApiPermission)
def deleteArtCharacter(illustID):
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    if not params:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    try:
        tagID = int(params.get("charaID"))
    except:
        return jsonify(
            status=400,
            message="charaID is invalid, or not specified."
        )
    isExist = g.db.has(
        "data_tag", "illustID=%s AND tagID=%s", (illustID, tagID,))
    if not isExist:
        return jsonify(
            status=400,
            message="The character is not registered to the art."
        )
    resp = g.db.edit(
        "DELETE FROM `data_tag` "
        + "WHERE illustID = %s AND tagID = %s",
        (illustID, tagID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Remove succeed.")


@arts_api.route(
    '/<int:illustID>/characters',
    methods=["GET"],
    strict_slashes=False
)
@auth.login_required
@limiter.limit(handleApiPermission)
def getArtCharacter(illustID):
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    '''指定されたイラスト付属のキャラ一覧を、フルデータとして取得する'''
    resp = g.db.get(
        f"""SELECT * FROM info_tag
        NATURAL JOIN
        (SELECT tagID FROM data_tag WHERE illustID=%s)
        WHERE tagType=1""",
        (illustID,)
    )
    if not len(resp):
        return jsonify(status=404, message="The art don't have any character.")
    return jsonify(
        status=200,
        message="found",
        data=[{
            "charaID": r[0],
            "name": r[1],
            "caption": r[2],
            "nsfw": r[3]
        } for r in resp]
    )


@arts_api.route(
    '/<int:illustID>/characters',
    methods=["PUT"],
    strict_slashes=False
)
@auth.login_required
@limiter.limit(handleApiPermission)
def addArtCharacter(illustID):
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    if not params:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    try:
        tagID = int(params.get("charaID"))
        isExist = g.db.has("info_tag", "tagID=%s", (tagID,))
        if tagID < 0 or not isExist:
            raise ValueError()
    except:
        return jsonify(
            status=400,
            message="tagID is invalid, or not specified."
        )
    isExist = g.db.has(
        "data_tag", "illustID=%s AND tagID=%s", (illustID, tagID,))
    if isExist:
        return jsonify(
            status=400,
            message="The character is already registered to the art."
        )
    resp = g.db.edit(
        "INSERT INTO `data_tag` (`illustID`,`tagID`) "
        + "VALUES (%s,%s);",
        (illustID, tagID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Add succeed.")

#
# イラストのいいね関連
#   無限にいいねできるものとする


@arts_api.route('/<int:illustID>/likes', methods=["PUT"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def addArtLike(illustID):
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    # いいね数を加算
    g.db.edit(
        """UPDATE data_illust
        SET illustLike = illustLike + 1
        WHERE illustID = %s""",
        (illustID,)
    )
    # いいね数を取得
    resp2 = g.db.get(
        "SELECT illustLike FROM data_illust WHERE illustID = %s",
        (illustID,)
    )
    # ランキングに追加
    now = datetime.now()
    resp = g.db.edit(
        f"""INSERT INTO data_ranking (
                rankingYear,
                rankingMonth,
                rankingDay,
                rankingDayOfWeek,
                illustID,
                illustLike
             ) VALUES (
                {now.year},
                {now.month},
                {now.day},
                {now.weekday()},
                {illustID},
                1
            )
            ON DUPLICATE KEY UPDATE
                illustLike = illustLike + VALUES(illustLike)"""
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Update succeed.", likes=resp2[0][0])


@arts_api.route(
    '/<int:illustID>/likes/<int:likeType>',
    methods=["PUT"],
    strict_slashes=False
)
@auth.login_required
@limiter.limit(handleApiPermission)
def addArtLikeWithType(illustID, likeType):
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    # イエロー/グリーン/レッド/ブルー
    # リクエストIDからいいね数変換
    likeDatas = {
        0: {"count": 1, "product_id": -1, "column": "illustStarYellow"},
        1: {"count": 10, "product_id": 18, "column": "illustStarGreen"},
        2: {"count": 20, "product_id": 19, "column": "illustStarRed"},
        3: {"count": 50, "product_id": 20, "column": "illustStarBlue"}
    }
    if likeType not in likeDatas.keys():
        return jsonify(status=400, message='Bad likeType')
    likeData = likeDatas[likeType]
    # ユーザーのカラースターを消費する
    if likeData["product_id"] != -1:
        toyApiKey = g.db.get(
            "SELECT userToyApiKey FROM data_user WHERE userID=%s",
            (g.userID,)
        )[0][0]
        resp = requests.post(
            f"{TOYMONEY_ENDPOINT}/users/assets/use",
            json={"id": likeData["product_id"], "amount": 1},
            headers={
                "Authorization": f"Bearer {toyApiKey}"
            }
        )
        if resp.status_code == 406:
            return jsonify(
                status=406,
                message="You need more power stars to open this door."
            )
    # いいね数を加算
    g.db.edit(
        """UPDATE data_illust
        SET illustLike = illustLike + %s
        WHERE illustID = %s""",
        (likeData["count"], illustID)
    )
    # スター数を加算
    g.db.edit(
        f"""UPDATE data_illust SET
        {likeData['column']} = {likeData['column']} + 1
        WHERE illustID = %s""",
        (illustID,)
    )
    # いいね数を取得
    resp2 = g.db.get(
        "SELECT illustLike FROM data_illust WHERE illustID = %s",
        (illustID,)
    )
    # ランキングに追加
    now = datetime.now()
    resp = g.db.edit(
        f"""INSERT INTO data_ranking (
                rankingYear,
                rankingMonth,
                rankingDay,
                rankingDayOfWeek,
                illustID,
                illustLike
             ) VALUES (
                {now.year},
                {now.month},
                {now.day},
                {now.weekday()},
                {illustID},
                {likeData['count']}
            )
            ON DUPLICATE KEY UPDATE
                illustLike = illustLike + VALUES(illustLike)"""
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Update succeed.", likes=resp2[0][0])


@arts_api.route(
    '/<int:illustID>/view',
    methods=["PUT"],
    strict_slashes=False
)
@auth.login_required
@limiter.limit(handleApiPermission)
def addArtView(illustID):
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    # 最終閲覧時刻から1時間以上経過していなければエラー
    if g.db.has(
        "data_view",
        f"""userID={g.userID}
        AND illustID={illustID}
        AND last_view > (NOW() - INTERVAL 1 HOUR)"""
    ):
        return jsonify(status=409, message="You can't add view for now")
    # 閲覧数を加算
    resp = g.db.edit(
        "UPDATE data_illust SET illustView = illustView + 1"
        + f" WHERE illustID={illustID}"
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    # 最終閲覧時刻を加算
    resp = g.db.edit(
        f"""INSERT INTO data_view (
            userID,illustID,last_view
            ) VALUES (
            {g.userID},
            {illustID},
            NOW()
            )
            ON DUPLICATE KEY UPDATE
                last_view = NOW()"""
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    # ランキングに追加
    now = datetime.now()
    resp = g.db.edit(
        f"""INSERT INTO data_ranking (
                rankingYear,
                rankingMonth,
                rankingDay,
                rankingDayOfWeek,
                illustID,
                illustView
             ) VALUES (
                {now.year},
                {now.month},
                {now.day},
                {now.weekday()},
                {illustID},
                1
            )
            ON DUPLICATE KEY UPDATE
                illustView = illustView + VALUES(illustView)"""
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Update view succeed.")


#
# イラストのコメント関連
#   無限にコメントできるものとする


@arts_api.route(
    '/<int:illustID>/comments',
    methods=["GET"],
    strict_slashes=False
)
@auth.login_required
@limiter.limit(handleApiPermission)
def getArtComments(illustID):
    per_page = 10
    pageID = request.args.get('page', default=1, type=int)
    if pageID < 1:
        pageID = 1
    sortMethod = request.args.get('sort', default="d", type=str)
    sortMethod = "commentID" if sortMethod == "d" else "commentUpdated"
    order = request.args.get('order', default="d", type=str)
    order = "DESC" if order == "d" else "ASC"
    resp = g.db.get(
        "SELECT userID, userName, commentID, "
        + "commentCreated, commentUpdated, commentBody "
        + "FROM data_comment NATURAL JOIN data_user "
        + f"WHERE illustID = {illustID} "
        + f"ORDER BY {sortMethod} {order} "
        + f"LIMIT {per_page} OFFSET {per_page * (pageID - 1)}"
    )
    if len(resp) == 0:
        return jsonify(
            status=200,
            message="ok",
            data=[]
        )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(
        status=200,
        message="ok",
        data=[
            {
                "user": {
                    "id": r[0],
                    "name": r[1]
                },
                "comment": {
                    "id": r[2],
                    "created": r[3].strftime('%Y-%m-%d %H:%M:%S'),
                    "updated": r[4].strftime('%Y-%m-%d %H:%M:%S'),
                    "body": r[5]
                }
            } for r in resp
        ]
    )


@arts_api.route(
    '/<int:illustID>/comments',
    methods=["POST"],
    strict_slashes=False
)
@auth.login_required
@limiter.limit(handleApiPermission)
def addArtComment(illustID):
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    if not params:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    if 'comment' not in params.keys():
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    comment = g.validate(params['comment'], lengthMax=500)
    resp = g.db.edit(
        """INSERT INTO data_comment
        (userID, illustID, commentBody)
        VALUES (%s, %s, %s)""",
        (g.userID, illustID, comment)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Create comment succeed.")


@arts_api.route(
    '/<int:illustID>/comments/<int:commentID>',
    methods=["PUT"],
    strict_slashes=False
)
@auth.login_required
@limiter.limit(handleApiPermission)
def editArtComment(illustID, commentID):
    if g.userPermission not in [9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    if not params:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    if 'comment' not in params.keys():
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    if not g.db.has(
        "data_comment",
        "commentID=%s AND illustID=%s",
        (commentID, illustID)
    ):
        return jsonify(status=404, message="The comment was not found.")
    comment = g.validate(params['comment'], lengthMax=500)
    resp = g.db.edit(
        "UPDATE data_comment SET "
        + "commentBody=%s, commentUpdated=CURRENT_TIMESTAMP() "
        + "WHERE commentID=%s AND illustID=%s",
        (comment, commentID, illustID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Update comment succeed.")


@arts_api.route(
    '/<int:illustID>/comments/<int:commentID>',
    methods=["DELETE"],
    strict_slashes=False
)
@auth.login_required
@limiter.limit(handleApiPermission)
def deleteArtComment(illustID, commentID):
    if g.userPermission not in [9]:
        return jsonify(status=400, message='Bad request')
    if not g.db.has(
        "data_comment",
        "commentID=%s AND illustID=%s",
        (commentID, illustID)
    ):
        return jsonify(status=404, message="The comment was not found.")
    resp = g.db.edit(
        "DELETE FROM data_comment WHERE commentID=%s AND illustID=%s",
        (commentID, illustID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Delete comment succeed.")
