from flask import Blueprint, request, g, jsonify
from ..extensions import auth, token_serializer
from ..extensions import limiter, handleApiPermission
from .recorder import recordApiRequest

artists_api = Blueprint('artists_api', __name__)

#
# 絵師関連
#


@artists_api.route('/', methods=["POST"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def addArtist():
    # 全体管理者権限を要求(一般ユーザーは作品投稿時点で処理)
    if g.userPermission != 9:
        return jsonify(
            status=401,
            message="You don't have enough permissions."
        )
    # パラメータ検証
    params = request.get_json()
    if not params:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    if "artistName" not in params.keys():
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    try:
        params = {p: g.validate(params[p]) for p in params.keys()}
    except:
        return jsonify(status=400, message="Request parameter is invalid.")
    artistName = params.get('artistName')
    # 既存の作者か確認
    if g.db.has("info_artist", "artistName=%s", (artistName,)):
        return jsonify(status=409, message="The artist is already exist.")
    # 変数を1つずつ取り出す
    artistDescription = params.get('artistDescription', None)
    groupName = params.get('groupName', None)
    pixivID = params.get('pixivID', None)
    twitterID = params.get('twitterID', None)
    mastodon = params.get('mastodon', None)
    homepage = params.get('homepage', None)
    userID = g.userID
    resp = g.db.edit(
        "INSERT INTO `info_artist`(`userID`,`artistName`,`artistDescription`,`groupName`,`pixivID`,`twitterID`,`mastodon`,`homepage`) VALUES (%s,%s,%s,%s,%s,%s,%s,%s);",
        (userID, artistName, artistDescription, groupName,
         pixivID, twitterID, mastodon, homepage)
    )
    if resp:
        createdID = g.db.get(
            "SELECT artistID FROM info_artist WHERE artistName = %s", (
                artistName,)
        )[0][0]
        recordApiRequest(userID, "addArtist", param1=createdID)
        return jsonify(status=201, message="Created", artistID=createdID)
    else:
        return jsonify(status=500, message="Server bombed.")


@artists_api.route('/<int:artistID>', methods=["DELETE"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def removeArtist(artistID):
    # 全体管理者権限を要求
    if g.userPermission != 9:
        return jsonify(
            status=401,
            message="You don't have enough permissions."
        )
    if not g.db.has("info_artist", "artistID=%s", (artistID,)):
        return jsonify(status=404, message="Specified artist was not found")
    illustCount = g.db.get(
        "SELECT COUNT(artistID) FROM data_illust WHERE artistID = %s",
        (artistID,)
    )[0][0]
    # 参照されていたら データロック
    if illustCount != 0:
        return jsonify(
            status=409,
            message="The artist is locked by reference."
        )
    resp = g.db.edit(
        "DELETE FROM info_artist WHERE artistID = %s", (artistID,))
    if resp:
        recordApiRequest(g.userID, "removeArtist", param1=artistID)
        return jsonify(status=200, message="Delete succeed.")
    else:
        return jsonify(status=500, message="Server bombed.")


@artists_api.route('/<int:artistID>', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def getArtist(artistID):
    recordApiRequest(g.userID, "getArtist", param1=artistID)
    artistData = g.db.get(
        "SELECT * FROM info_artist WHERE artistID = %s", (artistID,)
    )
    if len(artistData) < 1:
        return jsonify(status=404, message="Specified artist was not found")
    artistData = artistData[0]
    return jsonify(status=200, data={
        "id": artistData[0],
        "userID": artistData[1],
        "name": artistData[2],
        "description": artistData[3],
        "group": artistData[4],
        "pixivID": artistData[5],
        "twitterID": artistData[6],
        "mastodon": artistData[7],
        "homepage": artistData[8]
    })


@artists_api.route('/<int:artistID>', methods=["PUT"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def editArtist(artistID):
    # 一般ユーザー もしくは 全体管理者権限を要求
    if g.userPermission not in [0, 9]:
        return jsonify(
            status=401,
            message="You don't have enough permissions."
        )
    params = request.get_json()
    if not params:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    validParams = [
        "artistName",
        "artistDescription",
        "groupName",
        "pixivID",
        "twitterID",
        "mastodon",
        "homepage"
    ]
    params = {p: params[p] for p in params.keys() if p in validParams}
    if not params:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    for p in params.keys():
        resp = g.db.edit(
            "UPDATE `info_artist` SET `%s`=%s WHERE artistID=%s" % (p),
            (params[p], artistID,)
        )
        recordApiRequest(g.userID, "editArtist", param1=p, param2=params[p])
        if not resp:
            return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Update succeed.")
