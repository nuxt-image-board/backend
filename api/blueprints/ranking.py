from flask import Blueprint, g, request, jsonify, current_app
from datetime import datetime, timedelta
from ..extensions import (
    auth, limiter, handleApiPermission, cache, record
)
import calendar


ranking_api = Blueprint('ranking_api', __name__)

#
# イラストのランキング関連
#


def getMylistCountDict(illustIDs):
    illustKey = ",".join([str(i) for i in illustIDs])
    mylistData = {
        i[0]: i[1]
        for i in g.db.get(
            "SELECT illustID, COUNT(mylistID) FROM data_mylist "
            + "GROUP BY illustID "
            + f"HAVING illustID IN ({illustKey})"
        )
    }
    mylistDict = {
        str(i): mylistData[i]
        if i in mylistData else 0
        for i in illustIDs
    }
    return mylistDict


def getMylistedDict(illustIDs):
    illustKey = ",".join([str(i) for i in illustIDs])
    mylistedData = g.db.get(
        f"""SELECT illustID FROM data_mylist
        WHERE mylistID IN
        (SELECT mylistID FROM info_mylist WHERE userID={g.userID})
        AND illustID IN ({illustKey})"""
    )
    mylistedData = [i[0] for i in mylistedData]
    mylistedDict = {
        str(i): True if i in mylistedData else False
        for i in illustIDs
    }
    return mylistedDict


def getCountResult(whereSql):
    illustCount = g.db.get(
        f"""SELECT COUNT(DISTINCT illustID) FROM data_ranking
            WHERE {whereSql}"""
    )
    return illustCount[0][0]


def getRankingResult(whereSql, illustCount, sortMethod):
    per_page = 20
    pageID = request.args.get('page', default=1, type=int)
    pageID = pageID if pageID > 1 else 1
    order = request.args.get('order', default="d", type=str)
    order = "DESC" if order == "d" else "ASC"
    pages, extra_page = divmod(illustCount, per_page)
    if extra_page > 0:
        pages += 1
    illusts = g.db.get(
        f"""SELECT
            data_illust.illustID,
            data_illust.artistID,
            illustName,
            illustDescription,
            illustDate,
            illustPage,
            SUM(data_ranking.illustLike) AS totalLike,
            SUM(data_ranking.illustView) AS totalView,
            illustOriginUrl,
            illustOriginSite,
            illustNsfw,
            artistName,
            illustExtension,
            illustStatus,
            rankingYear,
            rankingMonth,
            rankingDay
        FROM
            data_ranking
        INNER JOIN
            data_illust
        ON
            data_ranking.illustID = data_illust.illustID
        INNER JOIN
            info_artist
        ON
            data_illust.artistID = info_artist.artistID
        GROUP BY
            illustID
        HAVING
            {whereSql}
        ORDER BY
            {sortMethod} {order}
        LIMIT {per_page} OFFSET {per_page * (pageID - 1)}"""
    )
    # ないとページ番号が不正なときに爆発する
    if not len(illusts):
        return jsonify(
            status=200,
            message="not found",
            data={
                "title": "ランキング",
                "count": 0,
                "current": 1,
                "pages": 1,
                "imgs": []
            }
        )
    illustIDs = [i[0] for i in illusts]
    # マイリストされた回数を気合で取ってくる
    mylistDict = getMylistCountDict(illustIDs)
    # 自分がマイリストしたかどうかを気合で取ってくる
    mylistedDict = getMylistedDict(illustIDs)
    return jsonify(
        status=200,
        message="found",
        data={
            "title": "ランキング",
            "count": illustCount,
            "current": pageID,
            "pages": pages,
            "imgs": [{
                "illustID": i[0],
                "artistID": i[1],
                "title": i[2],
                "caption": i[3],
                "date": i[4].strftime('%Y-%m-%d %H:%M:%S'),
                "pages": i[5],
                "like": int(i[6]),
                "view": int(i[7]),
                "mylist": mylistDict[str(i[0])],
                "mylisted": mylistedDict[str(i[0])],
                "originUrl": i[8],
                "originService": i[9],
                "nsfw": i[10],
                "artist": {
                    "name": i[11]
                },
                "extension": i[12]
            } for i in illusts]
        }
    )


def getRanking(whereSql, sortMethod):
    illustCount = getCountResult(whereSql)
    if illustCount == 0:
        return jsonify(status=404, message="No matched illusts.")
    return getRankingResult(whereSql, illustCount, sortMethod)


@ranking_api.route('/daily/views', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=500, query_string=True)
def getDailyViewsRanking():
    now = datetime.now()
    whereSql = f"""rankingYear={now.year}
        AND rankingMonth={now.month}
        AND rankingDay={now.day}"""
    return getRanking(whereSql, "totalView")


@ranking_api.route('/daily/likes', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=300, query_string=True)
def getDailyLikesRanking():
    now = datetime.now()
    whereSql = f"""rankingYear={now.year}
        AND rankingMonth={now.month}
        AND rankingDay={now.day}"""
    return getRanking(whereSql, "totalLike")


@ranking_api.route('/weekly/views', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=300, query_string=True)
def getWeeklyViewsRanking():
    now = datetime.now()
    if now.month > 1:
        month_days = calendar.monthrange(now.year, now.month-1)[1]
    else:
        month_days = calendar.monthrange(now.year-1, 12)[1]
    whereSql = f"""rankingYear={now.year} AND (
        (rankingMonth={now.month} AND rankingDay>={now.day-7})
        OR
        (
            rankingMonth={now.month-1} AND
            rankingDay>={month_days-((now.day-7)*-1)}
        ))"""
    return getRanking(whereSql, "totalView")


@ranking_api.route('/weekly/likes', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=300, query_string=True)
def getWeeklyLikesRanking():
    now = datetime.now()
    if now.month > 1:
        month_days = calendar.monthrange(now.year, now.month-1)[1]
    else:
        month_days = calendar.monthrange(now.year-1, 12)[1]
    whereSql = f"""rankingYear={now.year} AND (
        (rankingMonth={now.month} AND rankingDay>={now.day-7})
        OR
        (
            rankingMonth={now.month-1} AND
            rankingDay>={month_days-((now.day-7)*-1)}
        ))"""
    return getRanking(whereSql, "totalLike")


@ranking_api.route('/monthly/views', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=300, query_string=True)
def getMonthlyViewsRanking():
    year = request.args.get('year', default=datetime.now().year, type=int)
    month = request.args.get('month', default=datetime.now().month, type=int)
    whereSql = f"""rankingYear={year} AND rankingMonth={month}"""
    return getRanking(whereSql, "totalView")


@ranking_api.route('/monthly/likes', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
@cache.cached(timeout=300, query_string=True)
def getMonthlyLikesRanking():
    year = request.args.get('year', default=datetime.now().year, type=int)
    month = request.args.get('month', default=datetime.now().month, type=int)
    whereSql = f"""rankingYear={year} AND rankingMonth={month}"""
    return getRanking(whereSql, "totalLike")
