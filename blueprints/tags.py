from flask import Blueprint, g, request, jsonify, escape
from .authorizator import auth,token_serializer
from .limiter import apiLimiter,handleApiPermission
from .recorder import recordApiRequest

tags_api = Blueprint('tags_api', __name__)

#
# タグ関連
#

@tags_api.route('/',methods=["POST"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def addTag():
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    if "tagName" not in params.keys():
        return jsonify(status=400, message="Request parameters are not satisfied.")
    try:
        params = {p: g.validate(params[p]) for p in params.keys()}
    except:
        return jsonify(status=400, message="Request parameter is invalid.")
    tagName = params.get('tagName')
    if g.db.has("info_tag","tagName=?",(tagName,)):
        return jsonify(status=409, message="The tag is already exist.")
    tagDescription = params.get('tagDescription', None)
    nsfw = params.get('nsfw', None)
    if nsfw in [1,"True","true"]:
        nsfw = 1
    else:
        nsfw = 0
    resp = g.db.edit(
        "INSERT INTO `info_tag`(`tagName`,`tagDescription`,`nsfw`,`tagEndpoint`) VALUES (?,?,?,NULL);",
        (tagName, tagDescription, nsfw)
    )
    if resp:
        createdID = g.db.get(
            "SELECT tagID FROM info_tag WHERE tagName = ?",(tagName,)
        )[0][0]
        return jsonify(status=200, message="Created", tagID=createdID)
    else:
        return jsonify(status=500, message="Server bombed.")

@tags_api.route('/<int:tagID>/',methods=["DELETE"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def removeTag(tagID):
    if not g.db.has("info_tag","tagID=?",(tagID,)):
        return jsonify(status=404, message="Specified tag was not found")
    illustCount = g.db.get(
        "SELECT COUNT(tagID) FROM illust_tag WHERE tagID = ?", (tagID,)
    )[0][0]
    if not illustCount:
        return jsonify(status=409, message="The tag is locked by reference.")
    resp = g.db.edit("DELETE FROM info_tag WHERE tagID = ?", (tagID,))
    if resp:
        return jsonify(status=200, message="Delete succeed.")
    else:
        return jsonify(status=500, message="Server bombed.")
    
@tags_api.route('/<int:tagID>/',methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def getTag(tagID):
    tagData = g.db.get(
        "SELECT * FROM info_tag WHERE tagID = ?", (tagID,)
    )
    if len(tagData) < 1:
        return jsonify(status=404, message="Specified tag was not found")
    tagData = tagData[0]
    return jsonify(status=200, data={
        "id": tagData[0],
        "name": tagData[1],
        "description": tagData[2],
        "nsfw": tagData[3],
        "endpoint": tagData[4]
    })
    
@tags_api.route('/<int:tagID>/',methods=["PUT"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def editTag(tagID):
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    validParams = [
        "tagName",
        "tagDescription",
        "nsfw",
        "endpoint"
    ]
    params = {p:params[p] for p in params.keys() if p in validParams}
    if not params:
        return jsonify(status=400, message="Request parameters are invalid.")
    for p in params.keys():
        resp = g.db.edit(
            "UPDATE `info_tag` SET `%s`=? WHERE tagID=?"%(p),
            (params[p],tagID,)
        )
        if not resp:
            return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Update succeed.")