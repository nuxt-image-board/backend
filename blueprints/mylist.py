from flask import Flask, g, request, jsonify, Blueprint, current_app
from .authorizator import auth
from .limiter import apiLimiter, handleApiPermission
from .recorder import recordApiRequest

mylist_api = Blueprint('mylist_api', __name__)


@mylist_api.route('/', methods=["POST"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def createMylist():
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    mylistCount = g.db.get(
        "SELECT COUNT(mylistID) FROM info_mylist WHERE userID=%s",
        (g.userID,)
    )
    if mylistCount:
        if mylistCount[0][0] > 9:
            return jsonify(status=400, message="You have too many mylists, delete one and try again.")
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    name = params.get("name", "")
    description = params.get("description", "")
    if not name:
        return jsonify(status=400, message="name is required to create mylist")
    resp = g.db.edit(
        "INSERT INTO info_mylist (mylistName, mylistDescription, userID) "
        + "VALUES (%s,%s,%s)",
        (name, description, g.userID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    mylistID = g.db.get(
        "SELECT MAX(mylistID) FROM info_mylist WHERE userID=%s",
        (g.userID,)
    )[0][0]
    return jsonify(status=201, message="created", data={"mylistID": mylistID})


@mylist_api.route('/<int:mylistID>', methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def getMylist(mylistID):
    if not g.db.has("info_mylist", "mylistID=%s", (mylistID,)):
        return jsonify(status=404, message="The mylist was not exists")
    # マイリストの所有者を確認
    if not g.db.has(
        "info_mylist",
        "(userID=%s AND mylistID=%s) OR (mylistStatus=1 AND mylistID=%s)",
        (g.userID, mylistID, mylistID)
    ):
        return jsonify(status=400, message="You don't have permission")
    pageID = request.args.get('page', default=1, type=int)
    if pageID > 100:
        pageID = 100
    per_page = request.args.get('count', default=20, type=int)
    if per_page > 100:
        per_page = 100
    mylistName = g.db.get(
        "SELECT mylistName FROM info_mylist WHERE mylistID=%s",
        (mylistID, )
    )[0][0]
    illustCount = g.db.get(
        "SELECT COUNT(illustID) FROM data_mylist WHERE mylistID=%s",
        (g.userID,)
    )[0][0]
    pages, extra_page = divmod(illustCount, per_page)
    if extra_page > 0:
        pages += 1
    illusts = g.db.get(
        "SELECT illustID, data_illust.artistID, illustName, "
        + "illustDescription, illustDate, illustPage, illustLike, "
        + "illustOriginUrl, illustOriginSite, illustNsfw, artistName, "
        + "illustExtension FROM data_illust "
        + "INNER JOIN info_artist ON "
        + "data_illust.artistID = info_artist.artistID "
        + "WHERE illustID IN "
        + "( SELECT illustID FROM data_mylist WHERE mylistID = %s) "
        + "ORDER BY illustID DESC "
        + f"LIMIT {per_page} OFFSET {per_page*(pageID-1)}",
        (mylistID,)
    )
    recordApiRequest(
        g.userID,
        "getMylist",
        param1=per_page,
        param2=pageID
    )
    return jsonify(
        status=200,
        message="ok",
        data={
            "title": mylistName,
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


@mylist_api.route('/<int:mylistID>', methods=["PUT"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def editMylist(mylistID):
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    if not g.db.has("info_mylist", "mylistID=%s", (mylistID,)):
        return jsonify(status=404, message="The mylist was not exists")
    # マイリストの所有者を確認
    if not g.db.has(
        "info_mylist",
        "userID=%s AND mylistID=%s",
        (g.userID, mylistID)
    ):
        return jsonify(status=400, message="You don't have permission to edit")
    # パラメータ引き出し
    illustID = params.get("illustID", 0)
    action = params.get("action", "add")
    title = params.get("title", "")
    description = params.get("description", "")
    # マイリストのタイトルの変更
    if title:
        resp = g.db.edit(
            "UPDATE info_mylist SET mylistName = %s WHERE mylistID=%s",
            (title, mylistID,)
        )
        if not resp:
            return jsonify(status=500, message="Server bombed.")
    # マイリストの説明文の変更
    if description:
        resp = g.db.edit(
            "UPDATE info_mylist SET mylistDescription = %s WHERE mylistID=%s",
            (description, mylistID,)
        )
        if not resp:
            return jsonify(status=500, message="Server bombed.")
    # イラストの追加もしくは削除
    if action and illustID:
        # マイリスト内のデータ存在確認
        isExist = g.db.get(
            "SELECT illustID FROM data_mylist WHERE illustID=%s AND mylistID=%s",
            (illustID, mylistID)
        )
        # マイリストに追加
        if action == "add":
            if isExist:
                return jsonify(status=400, message="Already added to the list")
            resp = g.db.edit(
                "INSERT INTO data_mylist (mylistID, illustID) VALUES (%s, %s)",
                (mylistID, illustID)
            )
            if not resp:
                return jsonify(status=500, message="Server bombed.")
        # マイリストから削除
        else:
            if not isExist:
                return jsonify(status=400, message="Already deleted from the list")
            resp = g.db.edit(
                "DELETE FROM data_mylist WHERE mylistID=%s AND illustID=%s)",
                (mylistID, illustID)
            )
            if not resp:
                return jsonify(status=500, message="Server bombed.")
    resp = g.db.edit(
        "UPDATE info_mylist SET mylistUpdatedDate = CURRENT_TIMESTAMP() WHERE mylistID=%s",
        (mylistID, )
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="update complete")


@mylist_api.route('/list', methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def listMylist():
    userID = request.args.get('userID', default=g.userID, type=int)
    userName = g.db.get(
        "SELECT userName FROM data_user WHERE userID=%s",
        (userID,)
    )[0][0]
    mylistCount = g.db.get(
        "SELECT COUNT(mylistID) FROM info_mylist WHERE userID=%s",
        (userID,)
    )[0][0]
    if userID != g.userID:
        datas = g.db.get(
            "SELECT * FROM info_mylist "
            + "WHERE userID=%s AND mylistStatus=1 "
            + "ORDER BY mylistID DESC",
            (userID,)
        )
    else:
        datas = g.db.get(
            "SELECT * FROM info_mylist "
            + "WHERE userID=%s "
            + "ORDER BY mylistID DESC",
            (userID,)
        )
    recordApiRequest(
        g.userID,
        "listMylist",
        param1=userID,
        param2=mylistCount
    )
    return jsonify(
        status=200,
        message="found",
        data={
            "title": f"{userName} さんのマイリスト",
            "count": mylistCount,
            "current": 1,
            "pages": 1,
            "contents": [{
                "id": d[0],
                "name": d[2],
                "description": d[3],
                "createdDate": d[4],
                "updatedDate": d[5]
            } for d in datas]
        }
    )
