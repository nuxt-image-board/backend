from flask import Blueprint, request, g, jsonify
from .authorizator import auth, token_serializer
from .limiter import apiLimiter, handleApiPermission
from .recorder import recordApiRequest

forum_api = Blueprint('forum_api', __name__)

#
# 掲示板関連
#


@forum_api.route('/', methods=["POST"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def addThread():
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    if "charaName" not in params.keys():
        return jsonify(status=400, message="Request parameters are not satisfied.")
    params = {p: g.validate(params[p]) for p in params.keys()}
    charaName = params.get('charaName')
    if g.db.has("info_tag", "tagName=%s", (charaName,)):
        return jsonify(status=409, message="The Thread is already exist.")
    charaDescription = params.get('charaDescription', None)
    resp = g.db.edit(
        "INSERT INTO `info_tag`(`userID`,`tagName`,`tagDescription`,`tagNsfw`,`tagType`) VALUES (%s,%s,%s,0,1)",
        (g.userID, charaName, charaDescription, )
    )
    if resp:
        createdID = g.db.get(
            "SELECT tagID FROM info_tag WHERE tagName=%s", (charaName,)
        )[0][0]
        return jsonify(status=200, message="Created", charaID=createdID)
    else:
        return jsonify(status=500, message="Server bombed.")


@forum_api.route('/<int:charaID>', methods=["DELETE"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def removeThread(charaID):
    if not g.db.has("info_tag", "tagID=%s", (charaID,)):
        return jsonify(status=404, message="Specified Thread was not found")
    illustCount = g.db.get(
        "SELECT COUNT(tagID) FROM data_tag WHERE tagID =%s", (charaID,)
    )[0][0]
    if illustCount != 0:
        return jsonify(status=409, message="The Thread is locked by reference.")
    resp = g.db.edit("DELETE FROM info_tag WHERE tagID = %s", (charaID,))
    if resp:
        return jsonify(status=200, message="Delete succeed.")
    else:
        return jsonify(status=500, message="Server bombed.")


@forum_api.route('/<int:charaID>', methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def getThread(charaID):
    charaData = g.db.get(
        "SELECT * FROM info_tag WHERE tagID=%s AND tagType=1", (charaID,)
    )
    if len(charaData) < 1:
        return jsonify(status=404, message="Specified Thread was not found")
    charaData = charaData[0]
    # print(charaData)
    return jsonify(status=200, data={
        "id": charaData[0],
        "name": charaData[3],
        "description": charaData[4],
        "nsfw": charaData[5]
    })


@forum_api.route('/<int:charaID>', methods=["PUT"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def editThread(charaID):
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    validParams = {
        "charaName": "tagName",
        "charaDescription": "tagDescription"
    }
    params = {validParams[p]: params[p]
              for p in params.keys() if p in validParams.keys()}
    for p in params.keys():
        resp = g.db.edit(
            "UPDATE `info_tag` SET `%s`=%s WHERE tagID=%s" % (p),
            (params[p], charaID,)
        )
        if not resp:
            return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Update succeed.")
