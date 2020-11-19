from flask import Flask, g, request, jsonify, Blueprint, current_app
from .authorizator import auth
from ..extensions.limiter import limiter, handleApiPermission
from .recorder import recordApiRequest
from .lib.onesignal_client import OneSignalWrappedClient

notify_api = Blueprint('notify_api', __name__)


@notify_api.route('/setting/line', methods=["POST"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def initLineNotify():
    """
    LINE Notifyを使う
    """
    return jsonify(status=503, message="Not implemented.")


@notify_api.route('/setting/twitter', methods=["POST"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def initTwitterNotify():
    return jsonify(status=503, message="Not implemented.")


@notify_api.route('/setting/onesignal', methods=["POST"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def initOneSignalNotify():
    """
    サイト内で取得した OneSignalのPlayerIDをPOSTで送ってくる。
    """
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    if "id" not in params.keys():
        return jsonify(status=400, message="Request parameters are not satisfied.")
    # まず現状のデータをとってくる
    resp = g.db.get(
        "SELECT userOneSignalID FROM data_user WHERE userID=%s",
        (g.userID,)
    )
    # 存在するなら追加する
    if resp[0][0]:
        if params["id"] not in resp[0][0]:
            params["id"] += "," + resp[0][0]
        else:
            return jsonify(status=409, message="Duplicated playerID.")
    # 変な値のインジェクションがされる可能性あるけど　ここに変なデータ入れて何ができるだろう
    resp = g.db.edit(
        "UPDATE data_user SET userOneSignalID=%s WHERE userID=%s",
        (params["id"], g.userID)
    )
    if resp:
        return jsonify(status=200, message="Registered.")
    else:
        return jsonify(status=400, message="Maximum devices exceeded.")


@notify_api.route('/setting/onesignal', methods=["DELETE"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def resetOneSignalNotify():
    resp = g.db.edit(
        "UPDATE data_user SET userOneSignalID=NULL WHERE userID=%s",
        (g.userID,)
    )
    if resp:
        return jsonify(status=200, message="Deleted onesignal settings.")
    else:
        return jsonify(status=500, message="Server bombed.")


@notify_api.route('/register', methods=["POST"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def addNotify():
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    if "type" not in params.keys()\
            or "id" not in params.keys()\
            or "method" not in params.keys():
        return jsonify(status=400, message="Request parameters are not satisfied.")
    try:
        params = {p: int(params[p]) for p in params.keys()}
    except Exception as e:
        return jsonify(status=400, message="Request parameters are invalid.")
    resp = g.db.edit(
        "INSERT INTO data_notify (userID, targetType, targetID, targetMethod) VALUES (%s,%s,%s,%s)",
        (g.userID, params["type"], params["id"], params["method"])
    )
    if resp:
        createdID = g.db.get(
            "SELECT MAX(notifyID) FROM data_notify"
        )[0][0]
        # 設定変更の通知を送る
        if params["method"] == 0:
            userOneSignalID = g.db.get(
                "SELECT userOneSignalID FROM data_user WHERE userID=%s",
                (g.userID,)
            )[0][0]
            recordApiRequest(g.userID, "addNotify", param1=createdID)
            if userOneSignalID:
                userOneSignalID = userOneSignalID.split(",")
                cl = OneSignalWrappedClient(
                    current_app.config['onesignalAppId'],
                    current_app.config['onesignalToken']
                )
                cl.sendNotify(
                    userOneSignalID,
                    "通知設定が変更されました",
                    "新着イラストの通知はこのように送られます",
                )
        return jsonify(status=200, message="Registered.")
    else:
        return jsonify(status=500, message="Server bombed.")


@notify_api.route('/unregister', methods=["POST"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def deleteNotify():
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    if "type" not in params.keys()\
            or "id" not in params.keys()\
            or "method" not in params.keys():
        return jsonify(status=400, message="Request parameters are not satisfied.")
    try:
        params = {p: int(params[p]) for p in params.keys()}
    except Exception as e:
        return jsonify(status=400, message="Request parameters are invalid.")
    # 存在するか確認
    resp = g.db.get(
        "SELECT notifyID FROM data_notify WHERE userID=%s AND targetType=%s AND targetID=%s AND targetMethod=%s",
        (g.userID, params["type"], params["id"], params["method"])
    )
    if not len(resp):
        return jsonify(status=404, message="The notify was not found.")
    # 存在するなら削除
    resp = g.db.edit(
        "DELETE FROM data_notify WHERE userID=%s AND targetType=%s AND targetID=%s AND targetMethod=%s",
        (g.userID, params["type"], params["id"], params["method"])
    )
    if resp:
        recordApiRequest(
            g.userID,
            "removeNotify",
            param1=params["type"],
            param2=params["id"],
            param3=params["method"]
        )
        return jsonify(status=200, message="Delete succeed.")
    else:
        return jsonify(status=404, message="The notify was not found.")


@notify_api.route('/find', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def findNotify():
    '''方法も指定して通知が設定されているか確認'''
    targetType = request.args.get('type', default=None, type=int)
    targetID = request.args.get('id', default=None, type=int)
    targetMethod = request.args.get('method', default=None, type=int)
    recordApiRequest(
        g.userID,
        "findNotify",
        param1=targetType,
        param2=targetID,
        param3=targetMethod
    )
    if g.db.has(
        "data_notify",
        "userID=%s AND targetType=%s AND targetID=%s AND targetMethod=%s",
        (g.userID, targetType, targetID, targetMethod)
    ):
        return jsonify(
            status=200,
            message="The notify was found."
        )
    else:
        return jsonify(status=404, message="The notify was not found")


@notify_api.route('/finds', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def findsNotify():
    '''通知が設定されているか確認'''
    targetType = request.args.get('type', default=None, type=int)
    targetID = request.args.get('id', default=None, type=int)
    recordApiRequest(
        g.userID,
        "findsNotify",
        param1=targetType,
        param2=targetID
    )
    data = g.db.get(
        "SELECT * FROM data_notify "
        + "WHERE userID=%s AND targetType=%s AND targetID=%s",
        (g.userID, targetType, targetID,)
    )
    isOneSignalExists = True if [d for d in data if d[4] == 0] else False
    isLineExists = True if [d for d in data if d[4] == 1] else False
    isTwitterExists = True if [d for d in data if d[4] == 2] else False
    return jsonify(
        status=200,
        message="ok",
        data={
            "web": isOneSignalExists,
            "line": isLineExists,
            "twitter": isTwitterExists
        }
    )


@notify_api.route('/list', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def listNotify():
    pageID = request.args.get('page', default=1, type=int)
    per_page = request.args.get('count', default=50, type=int)
    if per_page > 100:
        per_page = 100
    notifyCount = g.db.get(
        "SELECT COUNT(DISTINCT notifyID) FROM data_notify WHERE userID=%s",
        (g.userID,)
    )[0][0]
    pages, extra_page = divmod(notifyCount, per_page)
    if extra_page > 0:
        pages += 1
    datas = g.db.get(
        "SELECT * FROM data_notify "
        + "WHERE userID=%s "
        + "ORDER BY notifyID DESC "
        + f"LIMIT {per_page} OFFSET {per_page*(pageID-1)}",
        (g.userID,)
    )
    recordApiRequest(
        g.userID,
        "listNotify",
        param1=per_page,
        param2=pageID
    )
    return jsonify(
        status=200,
        data={
            "title": "通知設定",
            "count": notifyCount,
            "current": pageID,
            "pages": pages,
            "contents": [{
                "type": d[2],
                "id": d[3],
                "method": d[4]
            } for d in datas]
        }
    )


@notify_api.route('/<int:notifyID>', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def getNotify(notifyID):
    resp = g.db.get(
        "SELECT * FROM data_notify WHERE notifyID=%s",
        (notifyID,)
    )
    if not len(resp):
        return jsonify(status=404, message="The notify was not found")
    resp = resp[0]
    return jsonify(
        status=200,
        data={
            "notifyID": resp[0],
            "type": resp[2],
            "id": resp[3],
            "method": resp[4]
        }
    )
