from flask import Blueprint, g, request, jsonify, escape, redirect
from ..extensions import (
    auth, token_serializer,
    limiter, handleApiPermission,
    cache, record
)
from datetime import datetime
import hashlib
import requests
import jwt
from os import environ
from dotenv import load_dotenv
load_dotenv(verbose=True, override=True)

accounts_api = Blueprint('accounts_api', __name__)

SALT_PASS = environ.get('SALT_PASS')
LINE_CHANNEL_ID = environ.get('AUTH_LINE_CHANNEL_ID')
LINE_CHANNEL_SECRET = environ.get('AUTH_LINE_CHANNEL_SECRET')
LINE_ENDPOINT = environ.get('AUTH_LINE_ENDPOINT')
LINE_REDIRECT_URI_LOGIN = environ.get('AUTH_LINE_REDIRECT_LOGIN')
LINE_REDIRECT_URI_CONNECT = environ.get('AUTH_LINE_REDIRECT_CONNECT')
NOTIFY_CHANNEL_ID = environ.get('AUTH_LINE_NOTIFY_ID')
NOTIFY_CHANNEL_SECRET = environ.get('AUTH_LINE_NOTIFY_SECRET')
NOTIFY_ENDPOINT = environ.get('AUTH_LINE_NOTIFY_ENDPOINT')
NOTIFY_REDIRECT_URI_CONNECT = environ.get('AUTH_LINE_NOTIFY_CONNECT')
TOYMONEY_ENDPOINT = environ.get('API_TOYMONEY_ENDPOINT')


def generateApiKey(accountID):
    apiSeq, apiPermission = g.db.get(
        "SELECT userApiSeq,userPermission FROM data_user WHERE userID=%s",
        (accountID,)
    )[0]
    token = token_serializer.dumps({
        'id': accountID,
        'seq': apiSeq + 1,
        'permission': apiPermission
    }).decode('utf-8')
    resp = g.db.edit(
        """UPDATE data_user SET userApiSeq=userApiSeq+1, userApiKey=%s
        WHERE userID=%s""",
        (token, accountID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return token


@accounts_api.route('/', methods=["POST"], strict_slashes=False)
@auth.login_required
def createAccount():
    # Web管理者権限以上を要求
    if g.userPermission < 5:
        return jsonify(
            status=403,
            message="You don't have enough permissions."
        )
    # 入力チェック
    params = request.get_json()
    if not params:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    if "displayID" not in params\
            or "username" not in params\
            or "password" not in params\
            or "inviteCode" not in params:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    displayID = g.validate(params["displayID"], lengthMax=20)
    username = g.validate(params["username"], lengthMax=20)
    inviteCode = g.validate(params["inviteCode"], lengthMax=10)
    # 招待コードが合ってるか確認
    if not g.db.has(
        "data_invite",
        "invitee IS NULL AND inviteCode=%s",
        (inviteCode,)
    ):
        return jsonify(status=400, message="The invite code is invalid.")
    # IDと名前の重複確認
    if g.db.has(
        "data_user",
        "userDisplayID=%s OR userName=%s",
        (displayID, username)
    ):
        return jsonify(
            status=409,
            message="userDisplayID or userName is already used."
        )
    # パスワード生成
    password = g.validate(params["password"], lengthMin=5, lengthMax=50)
    password = SALT_PASS+password
    password = hashlib.sha256(password.encode("utf8")).hexdigest()
    # ToyMoneyServerにリクエストする
    toyApiResp = requests.post(
        TOYMONEY_ENDPOINT + "/users/create",
        json={"name": displayID, "password": "***REMOVED***{displayID}"}
    )
    if toyApiResp.status_code != 200:
        return jsonify(status=500, message="Server bombed.")
    toyApiKey = toyApiResp.json()["apiKey"]
    # 新規アカウント作成
    resp = g.db.edit(
        "INSERT INTO `data_user`"
        + "(`userDisplayID`, `userName`,`userPassword`,`userToyApiKey`)"
        + " VALUES (%s,%s,%s,%s)",
        (displayID, username, password, toyApiKey)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    # 作成したユーザーID取得
    userID = g.db.get(
        """SELECT userID FROM data_user
        WHERE userDisplayID=%s AND userPassword=%s""",
        (displayID, password)
    )[0][0]
    # 使う招待コードを1つ取る
    inviteID = g.db.get(
        """SELECT inviteID FROM data_invite
        WHERE invitee IS NULL AND inviteCode=%s
        ORDER BY inviteID ASC LIMIT 1""",
        (inviteCode, )
    )[0][0]
    # 招待コードを利用済みにする
    resp = g.db.edit(
        "UPDATE data_invite SET invitee=%s, inviteUsed=%s WHERE inviteID=%s",
        (userID, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inviteID)
    )
    if not resp:
        print("招待コードを利用済みにできない！")
        return jsonify(status=500, message="Server bombed.")
    # APIキーを作る(INSERT/UPDATEも一緒にやってる)
    apiKey = generateApiKey(userID)
    # マイリストを作る
    resp = g.db.edit(
        "INSERT INTO info_mylist (mylistName, mylistDescription, userID) "
        + "VALUES (%s,%s,%s)",
        (username+"のマイリスト", "", userID)
    )
    # 記録する
    record(g.userID, "createAccount", param1=userID)
    record(g.userID, "generateApiKey", param1=userID)
    record(g.userID, "createMylist", param1=userID)
    return jsonify(
        status=201,
        message="created",
        apiKey=apiKey
    )


# APIリミットが必要だと思う
@accounts_api.route('/login/form', methods=["POST"])
def loginAccountWithForm():
    '''アカウント名とパスワード もしくはLINE認証コードでログイン'''
    params = request.get_json()
    if not params:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    # Telegramログイン
    if "hash" in params:
        # resp/hashが必要
        if "query" not in params:
            return jsonify(
                status=400,
                message="Request parameters are not satisfied."
            )
        # 応答のハッシュとパラメータのハッシュが一致するか確認
        resp = "\n".join(
            [p + "=" + params["query"][p] for p in params["query"].keys()]
        )
        resp_hash = hashlib.sha256(resp.encode("utf8")).hexdigest()
        param_hash = params["hash"]
        if resp_hash != param_hash:
            return jsonify(status=401, message="hash mismatch")
        telegramUserId = params["query"]["id"]
        if not g.db.has("data_user", "userTelegramID=%s", (telegramUserId,)):
            return jsonify(status=404, message="account not found")
        apiKey = g.db.get(
            "SELECT userApiKey FROM data_user WHERE userTelegramID=%s",
            (telegramUserId,)
        )[0][0]
        return jsonify(
            status=200,
            message="welcome back",
            apiKey=apiKey
        )
    # LINEログイン
    elif "code" in params:
        # codeが必要
        code = params["code"]
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        params = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": LINE_REDIRECT_URI_LOGIN,
            "client_id": LINE_CHANNEL_ID,
            "client_secret": LINE_CHANNEL_SECRET
        }
        lineResp = requests.post(
            LINE_ENDPOINT, headers=headers, data=params).json()
        if 'error' in lineResp:
            return jsonify(status=401, message="line authorization failed")
        lineIDToken = lineResp["id_token"]
        lineData = jwt.decode(
            lineIDToken,
            LINE_CHANNEL_SECRET,
            audience=LINE_CHANNEL_ID,
            issuer='https://access.line.me',
            algorithms=['HS256']
        )
        lineUserID = lineData["sub"]
        if not g.db.has("data_user", "userLineID=%s", (lineUserID,)):
            return jsonify(status=404, message="account not found")
        apiKey = g.db.get(
            "SELECT userApiKey FROM data_user WHERE userLineID=%s",
            (lineUserID,)
        )[0][0]
        return jsonify(
            status=200,
            message="welcome back",
            apiKey=apiKey
        )
    # ID/パスワードログイン
    else:
        # id/passwordが必要
        if not ("id" in params and "password" in params):
            return jsonify(
                status=400,
                message="Request parameters are not satisfied."
            )
        password = SALT_PASS+params["password"]
        password = hashlib.sha256(password.encode("utf8")).hexdigest()
        apiKey = g.db.get(
            """SELECT userApiKey FROM data_user
            WHERE userDisplayID=%s AND userPassword=%s""",
            (params["id"], password)
        )
        if not apiKey:
            return jsonify(status=404, message="account not found")
        return jsonify(
            status=200,
            message="welcome back",
            apiKey=apiKey[0][0]
        )


# APIリミットが必要だと思う
@accounts_api.route('/login/line', methods=["POST"])
def loginAccountWithLine():
    '''認可コードでログイン'''
    params = request.get_json()
    if not params:
        return jsonify(status=403, message="Direct access is not allowed.")
    if "code" not in params:
        return jsonify(status=403, message="Direct access is not allowed.")
    code = params["code"]
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    params = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": LINE_REDIRECT_URI_LOGIN,
        "client_id": LINE_CHANNEL_ID,
        "client_secret": LINE_CHANNEL_SECRET
    }
    lineResp = requests.post(
        LINE_ENDPOINT, headers=headers, data=params).json()
    if 'error' in lineResp:
        return jsonify(status=401, message="line authorization failed")
    lineIDToken = lineResp["id_token"]
    lineData = jwt.decode(
        lineIDToken,
        LINE_CHANNEL_SECRET,
        audience=LINE_CHANNEL_ID,
        issuer='https://access.line.me',
        algorithms=['HS256']
    )
    lineUserID = lineData["sub"]
    if not g.db.has("data_user", "userLineID=%s", (lineUserID,)):
        return jsonify(status=404, message="account not found")
    apiKey = g.db.get(
        "SELECT userApiKey FROM data_user WHERE userLineID=%s",
        (lineUserID,)
    )[0][0]
    return jsonify(
        status=200,
        message="welcome back",
        apiKey=apiKey
    )


@accounts_api.route('/<int:accountID>/connect/telegram', methods=["POST"])
@auth.login_required
@limiter.limit(handleApiPermission)
def connectTelegramAccount(accountID):
    # 一般権限&本人の要求 もしくは 全体管理者権限を要求
    if g.userID != accountID and g.userPermission < 9:
        return jsonify(
            status=403,
            message="You don't have enough permissions."
        )
    params = request.get_json()
    if not params:
        return jsonify(status=403, message="Direct access is not allowed.")
    if not ("resp" in params and "hash" in params):
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    # 応答のハッシュとパラメータのハッシュが一致するか確認
    resp = "\n".join(
        [p + "=" + params["resp"][p] for p in params["resp"].keys()]
    )
    resp_hash = hashlib.sha256(resp.encode("utf8")).hexdigest()
    param_hash = params["resp"]
    if resp_hash != param_hash:
        return jsonify(status=401, message="hash mismatch")
    telegramUserId = params["resp"]["id"]
    resp = g.db.edit(
        "UPDATE data_user SET userTelegramID=%s WHERE userID=%s",
        (telegramUserId, g.userID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    record(g.userID, "connectTelegramAccount", param1=accountID)
    return jsonify(status=200, message="ok")


@accounts_api.route('/<int:accountID>/connect/line', methods=["POST"])
@auth.login_required
@limiter.limit(handleApiPermission)
def connectLineAccount(accountID):
    # 一般権限&本人の要求 もしくは 全体管理者権限を要求
    if g.userID != accountID and g.userPermission < 9:
        return jsonify(
            status=403,
            message="You don't have enough permissions."
        )
    params = request.get_json()
    if not params:
        return jsonify(status=403, message="Direct access is not allowed.")
    if "code" not in params:
        return jsonify(status=403, message="Direct access is not allowed.")
    code = params["code"]
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    params = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": LINE_REDIRECT_URI_CONNECT,
        "client_id": LINE_CHANNEL_ID,
        "client_secret": LINE_CHANNEL_SECRET
    }
    lineResp = requests.post(
        LINE_ENDPOINT, headers=headers, data=params).json()
    if 'error' in lineResp:
        return jsonify(status=401, message="line authorization failed")
    lineIDToken = lineResp["id_token"]
    lineData = jwt.decode(
        lineIDToken,
        LINE_CHANNEL_SECRET,
        audience=LINE_CHANNEL_ID,
        issuer='https://access.line.me',
        algorithms=['HS256']
    )
    lineUserID = lineData["sub"]
    resp = g.db.edit(
        "UPDATE data_user SET userLineID=%s WHERE userID=%s",
        (lineUserID, g.userID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    record(g.userID, "connectLineAccount", param1=accountID)
    return jsonify(status=200, message="ok")


@accounts_api.route('/<int:accountID>/connect/line_notify', methods=["POST"])
@auth.login_required
@limiter.limit(handleApiPermission)
def connectLineNotify(accountID):
    # 一般権限&本人の要求 もしくは 全体管理者権限を要求
    if g.userID != accountID and g.userPermission < 9:
        return jsonify(
            status=403,
            message="You don't have enough permissions."
        )
    params = request.get_json()
    if not params:
        return jsonify(status=403, message="Direct access is not allowed.")
    if "code" not in params:
        return jsonify(status=403, message="Direct access is not allowed.")
    code = params["code"]
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    params = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": NOTIFY_REDIRECT_URI_CONNECT,
        "client_id": NOTIFY_CHANNEL_ID,
        "client_secret": NOTIFY_CHANNEL_SECRET
    }
    notifyResp = requests.post(
        NOTIFY_ENDPOINT,
        headers=headers,
        data=params
    )
    if notifyResp.status_code != 200:
        return jsonify(status=401, message="notify authorization failed")
    notifyToken = notifyResp.json()['access_token']
    resp = g.db.edit(
        "UPDATE data_user SET userLineToken=%s WHERE userID=%s",
        (notifyToken, g.userID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    record(g.userID, "connectLineNotify", param1=accountID)
    return jsonify(status=200, message="ok")


@accounts_api.route('/me', methods=["GET"])
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=15)
def getSelfAccount():
    resp = g.db.get(
        """SELECT
            data_user.userID,
            data_user.userDisplayID,
            data_user.userName,
            data_user.userFavorite,
            (
                CASE WHEN data_user.userLineID IS NOT NULL THEN 1 ELSE 0
                END
            ) AS isLineConnected,
            data_invite.inviteUsed AS registeredDate,
            data_inviter.userID AS inviterID,
            data_inviter.userName AS inviter,
            (
                SELECT
                    inviteID
                FROM
                    data_invite
                WHERE
                    inviter = data_user.userID
                    AND
                    invitee IS NULL
                ORDER BY inviteID DESC LIMIT 1
            ) AS inviteID,
            (
                SELECT
                    inviteCode
                FROM
                    data_invite
                WHERE
                    inviter = data_user.userID
                    AND
                    invitee IS NULL
                ORDER BY inviteID DESC LIMIT 1
            ) AS inviteCode,
            (
                SELECT
                    COUNT(invitee)
                FROM
                    data_invite
                WHERE
                    inviter = data_user.userID
            ) AS inviteCount,
            data_user.userInviteEnabled,
            (
                CASE WHEN data_user.userLineToken IS NOT NULL THEN 1 ELSE 0
                END
            ) AS isLineNotifyEnabled,
            data_user.userOneSignalID,
            data_user.userPermission
        FROM
            data_user
        LEFT OUTER JOIN
            data_invite
        ON
            data_invite.invitee = data_user.userID
        INNER JOIN
            data_user AS data_inviter
        ON
            data_inviter.userID = data_invite.inviter
        WHERE
            data_user.userApiKey = %s""",
        (g.userApiKey,)
    )[0]
    mylistID = g.db.get(
        "SELECT MIN(mylistID) FROM info_mylist WHERE userID = %s",
        (g.userID,)
    )[0][0]
    record(g.userID, "getAccount", param1=g.userID)
    return jsonify(
        status=200,
        message="ok",
        data={
            "userID": resp[0],
            "displayID": resp[1],
            "name": resp[2],
            "favorite": resp[3],
            "lineConnect": resp[4],
            "lineNotify": resp[12],
            "oneSignalNotify": resp[13],
            "permission": resp[14],
            "registeredDate": resp[5].strftime('%Y-%m-%d %H:%M:%S'),
            "inviter": {
                "id": resp[6],
                "name": resp[7]
            },
            "invite": {
                "id": resp[8],
                "code": resp[9] if resp[11] == 1 else "INVITE_IS_DISABLED",
                "invited": resp[10],
                "enabled": bool(int(resp[11]))
            },
            "mylist": {
                "id": mylistID
            },
            "apiKey": g.userApiKey
        }
    )


@accounts_api.route('/<int:accountID>', methods=["GET"])
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=5)
def getAccount(accountID):
    resp = g.db.get(
        """SELECT userID,userDisplayID,userName,userFavorite FROM data_user
        WHERE userID=%s""",
        (accountID,)
    )
    if not resp or accountID in [0, 1, 2]:
        return jsonify(status=404, message="The account data was not found.")
    resp = resp[0]
    record(g.userID, "getAccount", param1=accountID)
    return jsonify(
        status=200,
        message="ok",
        data={
            "userID": resp[0],
            "displayID": resp[1],
            "name": resp[2],
            "favorite": resp[3]
        }
    )


@accounts_api.route('/<int:accountID>/upload_history', methods=["GET"])
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=10, query_string=True)
def getUploadHistory(accountID):
    '''
    REQ
     sort=d(ate)
     order=d(esc)/a(sc)
     page=1
    '''
    if g.userID != accountID and g.userPermission < 9:
        return jsonify(
            status=400,
            message="You don't have enough permissions."
        )
    sortMethod = "uploadID"
    per_page = 20
    pageID = request.args.get('page', default=1, type=int)
    if pageID < 1:
        pageID = 1
    order = request.args.get('order', default="d", type=str)
    order = "DESC" if order == "d" else "ASC"
    uploadCount = g.db.get(
        f"SELECT COUNT(uploadID) FROM data_upload WHERE userID={accountID}"
    )
    if not uploadCount or accountID in [0, 1]:
        return jsonify(status=404, message="The account data was not found.")
    uploadCount = uploadCount[0][0]
    pages, extra_page = divmod(uploadCount, per_page)
    if extra_page > 0:
        pages += 1
    resp = g.db.get(
        "SELECT uploadID, uploadStartedDate, uploadFinishedDate, uploadStatus,"
        + f"illustID FROM data_upload WHERE userID={accountID}"
        + f" ORDER BY {sortMethod} {order}"
        + f" LIMIT {per_page} OFFSET {per_page*(pageID-1)}"
    )
    record(g.userID, "getUploadHistory", param1=accountID)
    contents = [
        {
            "uploadID": d[0],
            "started": d[1].strftime('%Y-%m-%d %H:%M:%S') if d[1] else None,
            "finished": d[2].strftime('%Y-%m-%d %H:%M:%S') if d[2] else None,
            "status": d[3],
            "illustID": d[4]
        } for d in resp
    ]
    return jsonify(
        status=200,
        message="ok",
        data={
            "title": "アップロード履歴",
            "count": uploadCount,
            "current": pageID,
            "pages": pages,
            "contents": contents
        }
    )


@accounts_api.route('/<int:accountID>/apiKey', methods=["GET"])
@auth.login_required
@limiter.limit(handleApiPermission)
def regenerateApiKey(accountID):
    if g.userID != accountID and g.userPermission < 9:
        return jsonify(
            status=403,
            message="You don't have enough permissions."
        )
    apiKey = generateApiKey(accountID)
    return jsonify(status=201, message="ok", apiKey=apiKey)


@accounts_api.route('/<int:accountID>', methods=["DELETE"])
@auth.login_required
@limiter.limit(handleApiPermission)
def destroyAccount(accountID):
    # 一般権限&本人の要求 もしくは 全体管理者権限を要求
    if g.userID != accountID and g.userPermission < 9:
        return jsonify(
            status=403,
            message="You don't have enough permissions."
        )
    resp = g.db.edit(
        "UPDATE illust_main SET userID=0 WHERE userID=?",
        (accountID,)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    resp = g.db.edit(
        "DELETE FROM `data_user` WHERE userID=%s",
        (accountID,)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    record(g.userID, "destroyAccount", param1=accountID)
    return jsonify(status=200, message="ok")


@accounts_api.route('/<int:accountID>', methods=["PUT"])
@auth.login_required
@limiter.limit(handleApiPermission)
def editAccount(accountID):
    # 一般権限&本人の要求 もしくは 全体管理者権限を要求
    if g.userID != accountID and g.userPermission < 9:
        return jsonify(
            status=403,
            message="You don't have enough permissions."
        )
    params = request.get_json()
    validParams = [
        "userDisplayID",
        "userName",
        "userPassword",
        "userOldPassword",
        "userFavorite",
        "userTheme",
        "userPermission",
        "userLineID",
        "userTwitterID",
    ]
    params = {
        p: g.validate(params[p])
        for p in params.keys() if p in validParams
    }
    if not params:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    for p in params.keys():
        if p == "userOldPassword":
            continue
        if p == "userPermission" and g.userPermission < 9:
            continue
        if p == "userPassword":
            params["userOldPassword"] = SALT_PASS+params["userOldPassword"]
            old_passwd = hashlib.sha256(
                params["userOldPassword"].encode("utf8")
            ).hexdigest()
            resp = g.db.get(
                "SELECT userID FROM data_user WHERE userPassword = %s",
                (old_passwd,)
            )
            if resp == []:
                return jsonify(status=400, message="password mismatch")
            params[p] = g.validate(params[p], lengthMin=5, lengthMax=50)
            params[p] = SALT_PASS+params[p]
            params[p] = hashlib.sha256(params[p].encode("utf8")).hexdigest()
        resp = g.db.edit(
            "UPDATE `data_user` SET `" + p + "`=%s WHERE userID=%s",
            (params[p], g.userID,)
        )
        if not resp:
            return jsonify(status=500, message="Server bombed.")
        record(
            g.userID,
            "editAccount",
            param1=accountID,
            param2=p,
            param3=params[p]
        )
    return jsonify(status=200, message="Update complete")
