from flask import Blueprint, request, g, jsonify
from .authorizator import auth,token_serializer
from .limiter import apiLimiter,handleApiPermission
from .recorder import recordApiRequest

artists_api = Blueprint('artists_api', __name__)

#
# 絵師関連
#

@artists_api.route('/', methods=["POST"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def addArtist():
    #一般ユーザもしくは全体管理者権限を要求
    if g.userPermission > 0 and g.permissions < 6:
        return jsonify(status=401, message="You don't have enough permissions.")
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    if "artistName" not in params.keys():
        return jsonify(status=400, message="Request parameters are not satisfied.")
    params = {p: g.validate(params[p]) for p in params.keys()}
    artistName = params.get('artistName')
    if g.db.has("info_artist","artistName=?",(artistName,)):
        return jsonify(status=409, message="The artist is already exist.")
    artistDescription = params.get('artistDescription', None)
    groupName = params.get('groupName', None)
    artistIcon = params.get('artistIcon', None)
    pixivID = params.get('pixivID', None)
    pixiv = "https://www.pixiv.net/member.php?id="+pixivID if pixivID else None
    twitterID = params.get('twitterID', None)
    twitter = "https://twitter.com/"+twitterID if twitterID else None
    mastodon = params.get('mastodon', None)
    homepage = params.get('homepage', None)
    resp = g.db.edit("INSERT INTO `info_artist`(`artistName`,`artistDescription`,`artistIcon`,`groupName`,`pixivID`,`pixiv`,`twitterID`,`twitter`,`mastodon`,`homepage`,`artistEndpoint`) VALUES (?,?,?,?,?,?,?,?,?,?,NULL);",(artistName,artistDescription,groupName,artistIcon,pixivID,pixiv,twitterID,twitter,mastodon,homepage))
    if resp:
        createdID = g.db.get(
            "SELECT artistID FROM info_artist WHERE artistName = ?",(artistName,)
        )[0][0]
        return jsonify(status=201, message="Created", artistID=createdID)
    else:
        return jsonify(status=500, message="Server bombed.")

@artists_api.route('/<int:artistID>', methods=["DELETE"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def removeArtist(artistID):
    #全体管理者権限を要求
    if g.userPermission > 0 and g.permissions < 6:
        return jsonify(status=401, message="You don't have enough permissions.")
    if not g.db.has("info_artist","artistID=?",(artistID,)):
        return jsonify(status=404, message="Specified artist was not found")
    illustCount = g.db.get(
        "SELECT COUNT(artistID) FROM illust_main WHERE artistID = ?", (artistID,)
    )[0][0]
    if not illustCount:
        return jsonify(status=409, message="The artist is locked by reference.")
    resp = g.db.edit("DELETE FROM info_artist WHERE artistID = ?", (artistID,))
    if resp:
        return jsonify(status=200, message="Delete succeed.")
    else:
        return jsonify(status=500, message="Server bombed.")

@artists_api.route('/<int:artistID>',methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def getArtist(artistID):
    artistData = g.db.get(
        "SELECT * FROM info_artist WHERE artistID = ?", (artistID,)
    )
    if len(artistData) < 1:
        return jsonify(status=404, message="Specified artist was not found")
    artistData = artistData[0]
    return jsonify(status=200, data={
        "id": artistData[0],
        "name": artistData[1],
        "description": artistData[2],
        "icon": artistData[3],
        "group": artistData[4],
        "pixivID": artistData[5],
        "pixiv": artistData[6],
        "twitterID": artistData[7],
        "twitter": artistData[8],
        "mastodon": artistData[9],
        "homepage": artistData[10]
    })
    
@artists_api.route('/<int:artistID>',methods=["PUT"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def editArtist(artistID):
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    validParams = [
        "artistName",
        "artistID",
        "artistIcon",
        "groupName",
        "pixivID",
        "twitterID",
        "homepage"
    ]
    params = {p:params[p] for p in params.keys() if p in validParams}
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    for p in params.keys():
        resp = g.db.edit(
            "UPDATE `info_artist` SET `%s`=? WHERE artistID=?"%(p),
            (params[p],artistID,)
        )
        if not resp:
            return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Update succeed.")