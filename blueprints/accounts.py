from flask import Blueprint, g, request, jsonify, escape
import hashlib
from .authorizator import auth,token_serializer
from .limiter import apiLimiter,handleApiPermission
from .recorder import recordApiRequest

accounts_api = Blueprint('accounts_api', __name__)

'''
アカウントAPI

アカウントの管理などは
難読化したAPIにやらせる
(リクエスト自体はRSAで暗号化させるようにするなどの予定)

[アカウント新規登録の流れ]
1. RECAPCHAをチェック
2. 管理者としてPOST
3. 必要情報(表示ID/ユーザー名/パスワード)をチェック
4. SALTなどをデータベースに登録

[API新規登録の流れ]
1. 管理者として指定されたユーザーIDにGETリクエスト
2. 指定ユーザーのデータベースのuserApiSeqを増加させる(APIキーを発行/再発行する)
3.　トークンを発行

[検証の流れ]
1. 読み込み
2. すべて一致しているか確認(ついでにuserPermissionも取得)
3. 大丈夫そうならログイン成功

Permission
 0: 一般ユーザ(部分書き込みと読み取り)
 2: モデレータ
 5: 管理者(サイト上で実行される)(埋め込みのため、念の為削除権限を持たせないで置く)
'''

@accounts_api.route('/force_generate_account',methods=["POST"], strict_slashes=False)
def createAccountForce():
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    if "displayId" not in params\
    or "username" not in params\
    or "password" not in params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    displayID = g.validate(params["displayId"],lengthMax=20)
    username = g.validate(params["username"],lengthMax=20)
    if g.db.has("user_main",
        "userDisplayID=? OR userName=?",
        (displayID, username)
    ):
        return jsonify(status=409, message="userDisplayID or userName is already used.")
    password = g.validate(params["password"],lengthMin=5,lengthMax=50)
    password = "***REMOVED***"+password
    password = hashlib.sha256(password.encode("utf8")).hexdigest()
    resp = g.db.edit(
        "INSERT INTO `user_main`(`userDisplayID`, `userName`,`userPassword`) VALUES (?,?,?)",
        (displayID, username, password)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    userID = g.db.get(
        "SELECT userID FROM user_main WHERE userDisplayID=? AND userPassword=?",
        (displayID, password)
    )[0][0]
    recordApiRequest(-1, "createAccount", param1=userID)
    return jsonify(status=201, message="created")
    
@accounts_api.route('/<int:accountId>/force_generate_apiKey',methods=["GET"])
def createApiKeyForce(accountId):
    apiSeq, apiPermission = g.db.get(
        "SELECT userApiSeq,userPermission FROM user_main WHERE userID=?",
        (accountId,)
    )[0]
    resp = g.db.edit(
        "UPDATE user_main SET userApiSeq = userApiSeq + 1 WHERE userID=?",
        (accountId,)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    token = token_serializer.dumps({
        'id': accountId,
        'seq': apiSeq + 1,
        'permission': apiPermission
    }).decode('utf-8')
    recordApiRequest(-1, "createApiKey", param1=accountId)
    return jsonify(status=201, message="ok", data={"token":"Bearer "+token})

@accounts_api.route('/',methods=["POST"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def createAccount():
    #Web管理者権限以上を要求
    if g.userPermission < 5:
        return jsonify(status=400, message="You don't have enough permissions.")
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    if "displayId" not in params\
    or "username" not in params\
    or "password" not in params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    displayID = g.validate(params["displayId"],lengthMax=20)
    username = g.validate(params["username"],lengthMax=20)
    if g.db.has("user_main",
        "userDisplayID=? OR userName=?",
        (displayID, username)
    ):
        return jsonify(status=409, message="userDisplayID or userName is already used.")
    password = g.validate(params["password"],lengthMin=5,lengthMax=50)
    password = "***REMOVED***"+password
    password = hashlib.sha256(password.encode("utf8")).hexdigest()
    resp = g.db.edit(
        "INSERT INTO `user_main`(`userDisplayID`, `userName`,`userPassword`) VALUES (?,?,?)",
        (displayID, username, password)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    userID = g.db.get(
        "SELECT userID FROM user_main WHERE userDisplayID=? AND userPassword=?",
        (displayID, password)
    )[0][0]
    recordApiRequest(g.userID, "createAccount", param1=userID)
    return jsonify(status=201, message="created")
    
@accounts_api.route('/<int:accountId>',methods=["GET"])
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def getAccount(accountId):
    resp = g.db.get(
        "SELECT userID,userDisplayID,userName,userFavorite FROM user_main WHERE userID=?",
        (accountId,)
    )
    if not resp or accountId in [0,1,2]:
        return jsonify(status=404, message="The account data was not found.")
    resp = resp[0]
    recordApiRequest(g.userID, "getAccount", param1=accountId)
    return jsonify(
        status=200,
        message="ok",
        data={
            "userID": resp[0],
            "userDisplayID": resp[1],
            "userName": resp[2],
            "userFavoriteCharacter": resp[3]
        }
    )

@accounts_api.route('/<int:accountId>/apiKey',methods=["GET"])
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def createApiKey(accountId):
    #Web管理者権限以上を要求
    #　これ、人のアカウントIDでもトークン取得できちゃうので危険...
    #　発行申請とAPIキー表示のエンドポイントを分ければ解決するけど、おかしな実装な気がする
    if g.userPermission < 5 or accountId in [1,2,3]:
        return jsonify(status=400, message="You don't have enough permissions.")
    apiSeq, apiPermission = g.db.get(
        "SELECT userApiSeq,userPermission FROM user_main WHERE userID=?",
        (accountId,)
    )[0]
    resp = g.db.edit(
        "UPDATE user_main SET userApiSeq = userApiSeq + 1 WHERE userID=?",
        (accountId,)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    token = token_serializer.dumps({
        'id': accountId,
        'seq': apiSeq + 1,
        'permission': apiPermission
    }).decode('utf-8')
    recordApiRequest(g.userID, "createApiKey", param1=accountId)
    return jsonify(status=201, message="ok", data={"token":"Bearer "+token})

@accounts_api.route('/<int:accountId>',methods=["DELETE"])
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def destroyAccount(accountId):
    #　一般権限&本人の要求 もしくは 全体管理者権限を要求
    if g.userID != accountId and g.permission < 9:
        return jsonify(status=400, message="You don't have enough permissions.")
    resp = g.db.edit(
        "UPDATE illust_main SET userID=0 WHERE userID",
        accountId
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    resp = g.db.edit(
        "DELETE FROM `user_main` WHERE userID=?",
        accountId
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    recordApiRequest(g.userID, "destroyAccount", param1=accountId)
    return jsonify(status=200, message="ok")

@accounts_api.route('/<int:accountId>',methods=["PUT"])
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def editAccount():
    #　一般権限&本人の要求 もしくは 全体管理者権限を要求
    if g.userID != accountId and g.permission < 9:
        return jsonify(status=403, message="You don't have enough permissions.")
    params = request.get_json()
    validParams = [
        "userDisplayID",
        "userName",
        "userPassword",
        "userFavorite",
        "userTheme",
        "userPermission"
    ]
    params = {p: g.validate(params[p]) for p in params.keys() if p in validParams}
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    for p in params.keys():
        if p == "userPermission" and g.permission < 9:
            continue
        if p == "userPassword":
            params[p] = g.validate(params[p],lengthMin=5,lengthMax=50)
            params[p] = "***REMOVED***"+password
            params[p] = hashlib.sha256(password.encode("utf8")).hexdigest()
        resp = g.db.edit(
            "UPDATE `user_main` SET `%s`=? WHERE userID=?"%(p),
            (params[p],userID,)
        )
        if not resp:
            return jsonify(status=500, message="Server bombed.")
        recordApiRequest(
            g.userID,
            "editAccount",
            param1=accountId,
            param2=p,
            param3=params[p]
        )
    return jsonify(status=200, message="Update complete")
    
@accounts_api.route('/<int:accountId>/favorites',methods=["GET"])
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def getAccountFavorites():
    return "Not implemeted"
    
@accounts_api.route('/<int:accountId>/favorites',methods=["PUT"])
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def editAccountFavorites():
    return "Not implemeted"
    
@accounts_api.route('/<int:accountId>/favorites',methods=["DELETE"])
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def deleteAccountFavorites():
    return "Not implemeted"