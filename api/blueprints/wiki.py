from flask import Blueprint, request, g, jsonify
from ..extensions import (
    auth, limiter, handleApiPermission, record
)


wiki_api = Blueprint('wiki_api', __name__)

#
# Wiki (マークダウン記法)の 追加/削除/編集/検索 をするエンドポイント
#


@wiki_api.route('/', methods=["POST"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def addArticle():
    params = request.get_json()
    if not params:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    for required in ["body", "targetType", "targetID"]:
        if required not in params.keys():
            return jsonify(
                status=400,
                message="Request parameters are not satisfied."
            )
    targetType = int(params.get('targetType'))
    if targetType > 2:
        return jsonify(status=400, message="Invalid targetType")
    targetID = int(params.get('targetID'))
    if targetID < 0:
        return jsonify(status=400, message="Invalid targetID")
    # まず存在するIDか確認
    findDict = {
        0: ["data_user", "userID", "user"],
        1: ["info_tag", "tagID", "tag"],
        2: ["info_artist", "artistID", "artist"]
    }
    find = findDict[targetType]
    if not g.db.has(find[0], f"{find[1]}=%s", (targetID,)):
        return jsonify(
            status=404,
            message=f"Specified {find[2]} was not found"
        )
    # リビジョン情報取得
    revision = g.db.get(
        "SELECT revision FROM data_wiki WHERE targetType=%s AND targetID=%s"
        + " ORDER BY revision DESC LIMIT 1",
        (targetType, targetID)
    )
    if len(revision) > 0:
        revision = revision[0][0] + 1
    else:
        revision = 1
    # ユーザー記事は本人のみが書ける
    if targetType == 0 and targetID != g.userID and g.userPermission < 9:
        return jsonify(
            status=400,
            message="You can't edit another user's article."
        )
    title = params.get('title', '')
    # とりあえず3000文字まで
    body = params.get('body')
    if len(body) > 3000:
        return jsonify(status=400, message="The article is too long")
    resp = g.db.edit(
        "INSERT INTO data_wiki"
        + " (articleTitle, articleBody, targetType,"
        + " targetID, userID, revision)"
        + " VALUES (%s,%s,%s,%s,%s,%s)",
        (title, body, targetType, targetID, g.userID, revision)
    )
    if resp:
        createdID = g.db.get(
            "SELECT articleID FROM data_wiki ORDER BY articleID DESC LIMIT 1"
        )[0][0]
        return jsonify(status=200, message="Created", articleID=createdID)
    else:
        return jsonify(status=500, message="Server bombed.")


@wiki_api.route('/<int:articleID>', methods=["DELETE"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def removeArticle(articleID):
    if not g.db.has("data_wiki", "articleID=%s", (articleID,)):
        return jsonify(status=404, message="Specified article was not found")
    if g.userPermission < 9:
        return jsonify(
            status=403,
            message="You do not have enough permissions."
        )
    resp = g.db.edit(
        "DELETE FROM data_wiki WHERE articleID = %s",
        (articleID,)
    )
    if resp:
        return jsonify(status=200, message="Delete succeed.")
    else:
        return jsonify(status=500, message="Server bombed.")


@wiki_api.route('/<int:articleID>', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def getArticle(articleID):
    articleData = g.db.get(
        "SELECT articleID, articleTitle, articleBody,"
        + " targetType, targetID, revision, createdTime, userID,"
        + " userName FROM data_wiki"
        + " NATURAL JOIN data_user WHERE articleID = %s",
        (articleID,)
    )
    if len(articleData) < 1:
        return jsonify(status=404, message="Specified article was not found")
    articleData = articleData[0]
    return jsonify(
        status=200,
        data={
            "id": articleData[0],
            "title": articleData[1],
            "body": articleData[2],
            "target": {
                "type": articleData[3],
                "id": articleData[4],
            },
            "revision": articleData[5],
            "date": articleData[6].strftime('%Y-%m-%d %H:%M:%S'),
            "user": {
                "id": articleData[7],
                "name": articleData[8]
            }
        }
    )


@wiki_api.route('/find', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def findArticle():
    '''記事が存在するか確認'''
    targetType = request.args.get('type', default=None, type=int)
    targetID = request.args.get('id', default=None, type=int)
    record(
        g.userID,
        "findArticle",
        param1=targetType,
        param2=targetID
    )
    resp = g.db.get(
        """SELECT articleID,revision FROM data_wiki
        WHERE targetType=%s AND targetID=%s ORDER BY revision DESC LIMIT 1""",
        (targetType, targetID,)
    )
    if len(resp) > 0:
        return jsonify(
            status=200,
            message="The article was found.",
            articleID=resp[0][0],
            revision=resp[0][1]
        )
    else:
        return jsonify(status=404, message="The article was not found")


@wiki_api.route('/<int:articleID>', methods=["PUT"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def editArticle(articleID):
    params = request.get_json()
    if not params:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    if not g.db.has(
        "data_wiki",
        "articleID=%s AND userID=%s",
        (articleID, g.userID)
    ):
        return jsonify(
            status=400,
            message="You can't edit the article."
        )
    validParams = {
        "title": "articleTitle",
        "body": "articleBody"
    }
    params = {
        validParams[p]: params[p]
        for p in params.keys() if p in validParams.keys()
    }
    for p in params.keys():
        resp = g.db.edit(
            "UPDATE `data_wiki` SET `%s`=%s WHERE articleID=%s" % (p),
            (params[p], articleID,)
        )
        if not resp:
            return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Update succeed.")
