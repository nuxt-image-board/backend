from flask import Blueprint, g, request, jsonify, escape, current_app
from ..extensions.auth import auth, token_serializer
from ..extensions.limiter import limiter, handleApiPermission
from ..extensions.cache import cache
from .recorder import recordApiRequest
from .lib.saucenao_client import SauceNaoImageSearch
from .lib.ascii2d_client import Ascii2dImageSearch
import json
from PIL import Image
import imagehash
from tempfile import TemporaryDirectory
from base64 import b64encode
from uuid import uuid4
import os.path
from imghdr import what as what_img
from imghdr import tests

ALLOWED_EXTENSIONS = ["gif", "png", "jpg", "jpeg", "webp"]

JPEG_MARK = b'\xff\xd8\xff\xdb\x00C\x00\x08\x06\x06' \
    b'\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n' \
    b'\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f'


def test_jpeg(h, f):
    """JPEG data in JFIF format"""
    if b'JFIF' in h[:23]:
        return 'jpeg'
    """JPEG with small header"""
    if len(h) >= 32 and 67 == h[5] and h[:32] == JPEG_MARK:
        return 'jpeg'
    """JPEG data in JFIF or Exif format"""
    if h[6:10] in (b'JFIF', b'Exif') or h[:2] == b'\xff\xd8':
        return 'jpeg'


tests.append(test_jpeg)


def isNotAllowedFile(filename):
    if filename == ""\
        or '.' not in filename\
        or (filename.rsplit('.', 1)[1].lower()
            not in ALLOWED_EXTENSIONS):
        return True
    return False


def getMylistCountDict(illustIDs):
    illustKey = ",".join([str(i) for i in illustIDs])
    mylistData = {
        i[0]: i[1]
        for i in g.db.get(
            f"""SELECT illustID, COUNT(mylistID) FROM data_mylist
            GROUP BY illustID
            HAVING illustID IN ({illustKey})"""
        )
    }
    mylistDict = {
        str(i): mylistData[i]
        if i in mylistData else 0
        for i in illustIDs
    }
    return mylistDict


def getMylistedDict(illustIDs):
    illustKey = ",".join([str(i) for i in illustIDs])
    mylistedData = g.db.get(
        f"""SELECT illustID FROM data_mylist
        WHERE mylistID IN
        (SELECT mylistID FROM info_mylist WHERE userID={g.userID})
        AND illustID IN ({illustKey})"""
    )
    mylistedData = [i[0] for i in mylistedData]
    mylistedDict = {
        str(i): True if i in mylistedData else False
        for i in illustIDs
    }
    return mylistedDict


def getSearchCountResult(whereSql, placeholder=()):
    illustCount = g.db.get(
        f"""SELECT COUNT(DISTINCT illustID) FROM data_illust
            WHERE {whereSql}""",
        placeholder
    )
    return illustCount[0][0]


def getSearchResult(whereSql, illustCount, resultTitle, placeholder=()):
    per_page = 20
    pageID = request.args.get('page', default=1, type=int)
    if pageID < 1:
        pageID = 1
    sortMethod = request.args.get('sort', default="d", type=str)
    sortMethod = "illustDate" if sortMethod == "d" else "illustLike"
    order = request.args.get('order', default="d", type=str)
    order = "DESC" if order == "d" else "ASC"
    pages, extra_page = divmod(illustCount, per_page)
    if extra_page > 0:
        pages += 1
    illusts = g.db.get(
        f"""SELECT illustID,data_illust.artistID,illustName,illustDescription,
        illustDate,illustPage,illustLike,
        illustOriginUrl,illustOriginSite,illustNsfw,artistName,
        illustExtension,illustStatus
        FROM data_illust INNER JOIN info_artist
        ON data_illust.artistID = info_artist.artistID
        WHERE {whereSql}
        AND illustStatus=0
        ORDER BY {sortMethod} {order}
        LIMIT {per_page} OFFSET {per_page * (pageID - 1)}""",
        placeholder
    )
    # ないとページ番号が不正なときに爆発する
    if not len(illusts):
        return jsonify(status=404, message="No matched illusts.")
    illustIDs = [i[0] for i in illusts]
    # マイリストされた回数を気合で取ってくる
    mylistDict = getMylistCountDict(illustIDs)
    # 自分がマイリストしたかどうかを気合で取ってくる
    mylistedDict = getMylistedDict(illustIDs)
    return jsonify(
        status=200,
        message="found",
        data={
            "title": resultTitle,
            "count": illustCount,
            "current": pageID,
            "pages": pages,
            "imgs": [{
                "illustID": i[0],
                "artistID": i[1],
                "title": i[2],
                "caption": i[3],
                "date": i[4].strftime('%Y-%m-%d %H:%M:%S'),
                "pages": i[5],
                "like": i[6],
                "mylist": mylistDict[str(i[0])],
                "mylisted": mylistedDict[str(i[0])],
                "originUrl": i[7],
                "originService": i[8],
                "nsfw": i[9],
                "artist": {
                    "name": i[10]
                },
                "extension": i[11]
            } for i in illusts]
        }
    )


def getSearch(whereSql, resultTitle, placeholder=()):
    illustCount = getSearchCountResult(whereSql, placeholder)
    if illustCount == 0:
        return jsonify(status=404, message="No matched illusts.")
    return getSearchResult(whereSql, illustCount, resultTitle, placeholder)


search_api = Blueprint('search_api', __name__)

#
# 検索結果画面 関連 (キーワード/タグ/作者/キャラ/画像 とかは全部パラメータで取る)
#


@search_api.route("/tag", methods=["GET"])
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=7, query_string=True)
def searchByTag():
    tagID = request.args.get('id', default=None, type=int)
    if not tagID:
        return jsonify(status=400, message="tagID is required.")
    tagName = g.db.get(
        "SELECT tagName FROM info_tag WHERE tagID = %s",
        (tagID,)
    )
    if not tagName:
        return jsonify(status=404, message="The tag was not found")
    whereSql = f"""illustID IN
        (SELECT illustID FROM data_tag WHERE tagID={tagID})"""
    return getSearch(whereSql, tagName[0][0])


@search_api.route("/artist", methods=["GET"])
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=7, query_string=True)
def searchByArtist():
    artistID = request.args.get('id', default=None, type=int)
    if not artistID:
        return jsonify(status=400, message="artistID is required.")
    artistName = g.db.get(
        "SELECT artistName FROM info_artist WHERE artistID = %s",
        (artistID,)
    )
    if not artistName:
        return jsonify(status=404, message="The artist was not found")
    whereSql = f"data_illust.artistID = {artistID}"
    return getSearch(whereSql, artistName[0][0])


@search_api.route("/uploader", methods=["GET"])
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=7, query_string=True)
def searchByUploader():
    uploaderID = request.args.get('id', default=None, type=int)
    if not uploaderID:
        return jsonify(status=400, message="uploaderID is required.")
    uploaderName = g.db.get(
        "SELECT userName FROM data_user WHERE userID = %s",
        (uploaderID,)
    )
    if not uploaderName:
        return jsonify(status=404, message="The user was not found")
    whereSql = f"data_illust.userID = {uploaderID}"
    return getSearch(whereSql, uploaderName[0][0])


@search_api.route("/character", methods=["GET"])
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=7, query_string=True)
def searchByCharacter():
    charaID = request.args.get('id', default=None, type=int)
    if not charaID:
        return jsonify(status=400, message="charaID is required.")
    charaName = g.db.get(
        "SELECT tagName FROM info_tag WHERE tagID = %s",
        (charaID,)
    )
    if not charaName:
        return jsonify(status=404, message="The chara was not found")
    whereSql = f"""illustID IN
        (SELECT illustID FROM data_tag WHERE tagID={charaID})"""
    return getSearch(whereSql, charaName[0][0])


@search_api.route("/keyword", methods=["GET"])
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=7, query_string=True)
def searchByKeyword():
    keyword = request.args.get("keyword", default=None, type=str)
    if not keyword:
        return jsonify(status=400, message="keyword is required.")
    whereSql = "illustName LIKE %s"
    return getSearch(whereSql, keyword, ("%"+keyword+"%",))


@search_api.route('/all', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=7, query_string=True)
def searchByAll():
    whereSql = "1 = 1"
    return getSearch(whereSql, "全て")


@search_api.route('/random', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def searchByRandom():
    '''
    REQ
        nsfw= 1/0
        artistID=NUMBER
        tagID=NUMBER
        charaID=NUMBER
    '''
    acceptNsfw = request.args.get('nsfw', default=0, type=int)
    artistID = request.args.get('artistID', default=0, type=int)
    tagID = request.args.get('tagID', default=0, type=int)
    charaID = request.args.get('charaID', default=0, type=int)
    count = request.args.get('count', default=1, type=int)
    acceptNsfw = 1 if acceptNsfw else 0
    count = 10 if count > 10 else count
    # 完全ランダム
    if (not artistID) and (not tagID) and (not charaID):
        illusts = g.db.get(
            f"""SELECT illustID, data_illust.artistID,
            illustName, illustDescription,
            illustDate, illustPage, illustLike, illustOriginUrl,
            illustOriginSite, illustNsfw, artistName,
            illustExtension,illustStatus
            FROM `data_illust` INNER JOIN info_artist
            ON info_artist.artistID = data_illust.artistID
            WHERE illustNsfw={acceptNsfw} AND illustStatus=0
            ORDER BY RAND() LIMIT {count}"""
        )
    # 作者指定ランダム
    elif artistID:
        illusts = g.db.get(
           f"""SELECT illustID, data_illust.artistID,
           illustName, illustDescription,
           illustDate, illustPage, illustLike, illustOriginUrl,
           illustOriginSite, illustNsfw, artistName,
           illustExtension, illustStatus
           FROM `data_illust` INNER JOIN info_artist
           ON info_artist.artistID = data_illust.artistID
           WHERE illustNsfw={acceptNsfw}
           AND data_illust.artistID={artistID}
           AND illustStatus=0
           ORDER BY RAND() LIMIT {count}"""
        )
    # タグ指定ランダム
    # キャラ指定ランダム
    else:
        # つまりタグIDなので握りつぶす
        if charaID:
            tagID = charaID
        illusts = g.db.get(
           f"""SELECT illustID, data_illust.artistID,
           illustName, illustDescription,
           illustDate, illustPage, illustLike, illustOriginUrl,
           illustOriginSite, illustNsfw, artistName,
           illustExtension, illustStatus
           FROM `data_illust` INNER JOIN info_artist
           ON info_artist.artistID = data_illust.artistID
           WHERE illustID IN
           (SELECT illustID FROM data_tag WHERE tagID={tagID})
           AND illustStatus=0
           AND illustNsfw={acceptNsfw} ORDER BY RAND() LIMIT {count}"""
        )
    if not illusts:
        return jsonify(404, message="No matched arts.")
    illustIDs = [i[0] for i in illusts]
    # マイリストされた回数を気合で取ってくる
    mylistDict = getMylistCountDict(illustIDs)
    return jsonify(
        status=200,
        message="found",
        data={
            "imgs": [{
                "illustID": illust[0],
                "artistID": illust[1],
                "title": illust[2],
                "caption": illust[3],
                "date": illust[4],
                "pages": illust[5],
                "like": illust[6],
                "mylist": mylistDict[str(illust[0])],
                "originUrl": illust[7],
                "originService": illust[8],
                "nsfw": illust[9],
                "artist": {
                    "name": illust[10]
                },
                "extension": illust[11]
            } for illust in illusts]
        }
    )


@search_api.route('/image/saucenao', methods=["POST"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def searchByImageAtSauceNao():
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message="Bad request")
    if "file" not in request.files:
        return jsonify(status=400, message="File must be included")
    file = request.files['file']
    # ファイル拡張子確認
    if isNotAllowedFile(file.filename):
        return jsonify(status=400, message="The file is not allowed")
    with TemporaryDirectory() as temp_path:
        # 画像を一旦保存して確認
        uniqueID = str(uuid4()).replace("-", "")
        uniqueID = b64encode(uniqueID.encode("utf8")).decode("utf8")[:-1]
        tempPath = os.path.join(temp_path, uniqueID)
        file.save(tempPath)
        fileExt = what_img(tempPath)
        if not fileExt:
            return jsonify(status=400, message="The file is not allowed")
        cl = SauceNaoImageSearch(
            current_app.config['imgurToken'],
            current_app.config['saucenaoToken']
        )
        result = cl.search(tempPath)
        return jsonify(
            status=200,
            message='ok',
            data={
                'result': result
            }
        )


@search_api.route('/image/ascii2d', methods=["POST"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def searchByImageAtAscii2d():
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message="Bad request")
    if "file" not in request.files:
        return jsonify(status=400, message="File must be included")
    file = request.files['file']
    # ファイル拡張子確認
    if isNotAllowedFile(file.filename):
        return jsonify(status=400, message="The file is not allowed")
    with TemporaryDirectory() as temp_path:
        # 画像を一旦保存して確認
        uniqueID = str(uuid4()).replace("-", "")
        uniqueID = b64encode(uniqueID.encode("utf8")).decode("utf8")[:-1]
        tempPath = os.path.join(temp_path, uniqueID)
        file.save(tempPath)
        fileExt = what_img(tempPath)
        if not fileExt:
            return jsonify(status=400, message="The file is not allowed")
        cl = Ascii2dImageSearch(
            current_app.config['imgurToken']
        )
        result = cl.search(tempPath)
        return jsonify(
            status=200,
            message='ok',
            data={
                'url': result["color"]["url"],
                'result': result["color"]["result"][:2]\
                    + result["bovw"]["result"][:2]\
                    + result["color"]["result"][2:4]\
                    + result["bovw"]["result"][2:4]
            }
        )


@search_api.route('/image', methods=["POST"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def searchByImage():
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message="Bad request")
    if "file" not in request.files:
        return jsonify(status=400, message="File must be included")
    file = request.files['file']
    # ファイル拡張子確認
    if isNotAllowedFile(file.filename):
        return jsonify(status=400, message="The file is not allowed")
    with TemporaryDirectory() as temp_path:
        # 画像を一旦保存して確認
        uniqueID = str(uuid4()).replace("-", "")
        uniqueID = b64encode(uniqueID.encode("utf8")).decode("utf8")[:-1]
        tempPath = os.path.join(temp_path, uniqueID)
        file.save(tempPath)
        fileExt = what_img(tempPath)
        if not fileExt:
            return jsonify(status=400, message="The file is not allowed")
        # 大丈夫そうなのでハッシュ値を作成して検索
        hash = int(str(imagehash.phash(Image.open(tempPath))), 16)
        # 検索SQL
        illusts = g.db.get(
            f"""SELECT illustID, data_illust.artistID,
            BIT_COUNT(illustHash ^ %s) AS SAME,
            illustName, illustDescription, illustDate, illustPage, illustLike,
            illustOriginUrl, illustOriginSite, illustNsfw, artistName,
            illustExtension,illustStatus
            FROM `data_illust`
            INNER JOIN info_artist
            ON info_artist.artistID = data_illust.artistID
            HAVING SAME < 5 AND illustStatus=0 ORDER BY SAME DESC LIMIT 10"""
            (hash,)
        )
        if len(illusts):
            illustIDs = [i[0] for i in illusts]
            # マイリストされた回数を気合で取ってくる
            mylistDict = getMylistCountDict(illustIDs)
            # 自分がマイリストしたかどうかを気合で取ってくる
            mylistedDict = getMylistedDict(illustIDs)
            illusts = [{
                "illustID": i[0],
                "artistID": i[1],
                "similarity": i[2],
                "title": i[3],
                "caption": i[4],
                "date": i[5].strftime('%Y-%m-%d %H:%M:%S'),
                "pages": i[6],
                "like": i[7],
                "mylist": mylistDict[str(i[0])],
                "mylisted": mylistedDict[str(i[0])],
                "originUrl": i[8],
                "originService": i[9],
                "nsfw": i[10],
                "artist": {
                    "name": i[11]
                },
                "extension": i[12]
            } for i in illusts]
        else:
            illusts = []
        # データベースから検索
        return jsonify(
            status=200,
            message='ok',
            data={
                'hash': str(hash),
                'illusts': illusts
            }
        )

#
# 高度な検索(複数タグ等)
#

# 複数条件での検索処理
# 1. まずキーワードからタグ一覧を取ってくる(tags/find から取ってくる)
# 2. タグ一覧を tagIdsとして渡して 応答に返ってくるイラストIDを取得する
# (TODO:search系列と同様の動作をするように修正)

# OR検索の例
# SELECT illustID,tagID FROM `data_tag` WHERE tagID IN (1,2,3)
#
# AND検索の例
#  SELECT illustID,tagID FROM `data_tag` GROUP BY illustID
#  HAVING SUM(tagID='1') AND SUM(tagID='2')
# または
#  SELECT illustID FROM テーブル WHERE tagID=? AND illustID
#  IN (それまでに取得したillustIDリスト)
#  を forで回せばいい


@search_api.route("/multiple/tag", methods=["GET"])
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=7, query_string=True)
def searchByMultipleTag():
    # パラメータの確認
    tagID = request.args.get('id', default=None, type=str)
    if not tagID:
        return jsonify(status=400, message="tagID is required.")
    # あんまり長いと負荷がかかりそうなので制限
    tagID = [str(int(t)) for t in tagID.split(',') if t.isdigit()]
    tagID = tagID[:5] if len(tagID) > 5 else tagID
    filterHaving = ' AND '.join([f"SUM(tagID='{t}')" for t in tagID])
    # カウント取得
    baseWhere = f"""
        (SELECT illustID FROM data_tag GROUP BY illustID HAVING {filterHaving})
    """
    illustCount = g.db.get(f"SELECT COUNT(illustID) FROM {baseWhere} AS T1")
    if not illustCount:
        return jsonify(status=404, message="No matched illusts.")
    # タグ名取得
    tagName = g.db.get(
        f"SELECT tagName FROM info_tag WHERE tagID In ({','.join(tagID)})"
    )
    tagName = " ".join([t[0] for t in tagName])
    # 検索結果取得
    whereSql = f"illustID IN {baseWhere}"
    return getSearchResult(whereSql, illustCount[0][0], tagName)
