from flask import Blueprint, g, request, jsonify, escape
from ..extensions import (
    auth, limiter, handleApiPermission, record
)

tags_api = Blueprint('tags_api', __name__)

#
# タグ関連
#


@tags_api.route('/', methods=["POST"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def addTag():
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    if not params:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    if "tagName" not in params.keys():
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    try:
        params = {p: g.validate(params[p]) for p in params.keys()}
    except:
        return jsonify(status=400, message="Request parameter is invalid.")
    tagName = params.get('tagName')
    if g.db.has("info_tag", "tagName=%s", (tagName,)):
        return jsonify(status=409, message="The tag is already exist.")
    tagDescription = params.get('tagDescription', None)
    try:
        tagType = int(params.get('tagType', 0))
        if tagType > 2:
            tagType = 0
    except:
        tagType = 0
    nsfw = params.get('nsfw', 0)
    if nsfw in ["1", 1, "True", "true"]:
        nsfw = "1"
    else:
        nsfw = "0"
    resp = g.db.edit(
        """INSERT INTO info_tag
        (userID,tagType,tagName,tagDescription,tagNsfw)
        VALUES (%s,%s,%s,%s,%s)""",
        (g.userID, tagType, tagName, tagDescription, nsfw)
    )
    if resp:
        createdID = g.db.get(
            "SELECT tagID FROM info_tag WHERE tagName = %s", (tagName,)
        )[0][0]
        return jsonify(status=200, message="Created", tagID=createdID)
    else:
        return jsonify(status=500, message="Server bombed.")


@tags_api.route('/<int:tagID>/', methods=["DELETE"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def removeTag(tagID):
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    if not g.db.has("info_tag", "tagID=%s", (tagID,)):
        return jsonify(status=404, message="Specified tag was not found")
    illustCount = g.db.get(
        "SELECT COUNT(tagID) FROM data_tag WHERE tagID = %s", (tagID,)
    )[0][0]
    if illustCount != 0:
        return jsonify(status=409, message="The tag is locked by reference.")
    resp = g.db.edit("DELETE FROM info_tag WHERE tagID = %s", (tagID,))
    if resp:
        return jsonify(status=200, message="Delete succeed.")
    else:
        return jsonify(status=500, message="Server bombed.")


@tags_api.route('/<int:tagID>/', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def getTag(tagID):
    tagData = g.db.get(
        "SELECT * FROM info_tag WHERE tagID = %s", (tagID,)
    )
    if len(tagData) < 1:
        return jsonify(status=404, message="Specified tag was not found")
    tagData = tagData[0]
    return jsonify(status=200, data={
        "id": tagData[0],
        "user": tagData[1],
        "type": tagData[2],
        "name": tagData[3],
        "description": tagData[4],
        "nsfw": tagData[5]
    })


@tags_api.route('/<int:tagID>/', methods=["PUT"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def editTag(tagID):
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    if not params:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    validParams = {
        "name": "tagName",
        "description": "tagDescription",
        "nsfw": "tagNsfw",
        "type": "tagType"
    }
    tagData = g.db.get(
        "SELECT * FROM info_tag WHERE tagID = %s", (tagID,)
    )
    if len(tagData) < 1:
        return jsonify(status=404, message="Specified tag was not found.")
    if (g.userID != tagData[0][2]) and g.userPermission != 9:
        return jsonify(status=401, message="You don't have enough permission.")
    params = {
        validParams[p]: params[p]
        for p in params.keys()
        if p in validParams.keys()
    }
    if not params:
        return jsonify(status=400, message="Request parameters are invalid.")
    for p in params.keys():
        resp = g.db.edit(
            "UPDATE `info_tag` SET `%s`=%s WHERE tagID=%s" % (p),
            (params[p], tagID,)
        )
        if not resp:
            return jsonify(
                status=400,
                message="The tagName is already exists."
            )
    return jsonify(status=200, message="Update succeed.")


@tags_api.route('/finds', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def getTagListByKeyword():
    keyword = request.args.get('keyword', default=None, type=str)
    resp = g.db.get(
        "SELECT tagID,tagName FROM info_tag "
        + "WHERE tagName LIKE %s ORDER BY tagID ASC LIMIT 20",
        (f'%{keyword}%',)
    )
    if len(resp) == 0:
        return jsonify(
            status=404,
            message="not found"
        )
    return jsonify(
        status=200,
        message="ok",
        data=[{'id': r[0], 'name':r[1]} for r in resp]
    )
