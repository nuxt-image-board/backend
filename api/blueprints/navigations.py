from flask import Blueprint, jsonify, g
from ..extensions import (
    auth, limiter, handleApiPermission, cache, record
)

navigations_api = Blueprint('navigations_api', __name__)

# ナビゲーション


@navigations_api.route("/characters", methods=["GET"])
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=300)
def getCharactersNavigation():
    datas = g.db.get(
        f"""SELECT tagName, data_tag.tagID, COUNT(data_tag.tagID) AS CNT
        FROM data_tag INNER JOIN info_tag ON info_tag.tagID = data_tag.tagID
        WHERE tagType = 1 GROUP BY data_tag.tagID ORDER BY CNT DESC LIMIT 5 """
    )
    ls = [{"name": d[0], "id":d[1], "count":d[2]} for d in datas]
    return jsonify(status=200, data=ls)


@navigations_api.route("/artists", methods=["GET"])
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=300)
def getArtistsNavigation():
    datas = g.db.get(
        f"""SELECT artistName,data_illust.artistID,COUNT(data_illust.artistID)
        FROM info_artist
        INNER JOIN data_illust ON info_artist.artistID = data_illust.artistID
        GROUP BY data_illust.artistID
        ORDER BY COUNT(data_illust.artistID) DESC LIMIT 5"""
    )
    ls = [{"name": d[0], "id":d[1], "count":d[2]} for d in datas]
    return jsonify(status=200, data=ls)


@navigations_api.route("/tags", methods=["GET"])
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=300)
def getTagsNavigation():
    datas = g.db.get(
        f"""SELECT tagName, data_tag.tagID, COUNT(data_tag.tagID) AS CNT
        FROM data_tag INNER JOIN info_tag ON info_tag.tagID = data_tag.tagID
        WHERE tagType = 0
        GROUP BY data_tag.tagID
        ORDER BY CNT DESC LIMIT 5 """
    )
    ls = [{"name": d[0], "id":d[1], "count":d[2]} for d in datas]
    return jsonify(status=200, data=ls)


@navigations_api.route("/uploaders", methods=["GET"])
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=300)
def getUploadersNavigation():
    datas = g.db.get(
        f"""SELECT userName, data_user.userID, COUNT(data_user.userID) AS CNT
        FROM data_user
        INNER JOIN data_illust ON data_user.userID = data_illust.userID
        GROUP BY data_user.userID
        ORDER BY CNT DESC LIMIT 5 """
    )
    ls = [{"name": d[0], "id":d[1], "count":d[2]} for d in datas]
    return jsonify(status=200, data=ls)
