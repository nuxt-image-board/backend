from flask import Flask, g, request, jsonify, Blueprint
from ..extensions import (
    auth, limiter, handleApiPermission, record
)


superuser_api = Blueprint('superuser_api', __name__)


@superuser_api.route('/gc', methods=["GET"], strict_slashes=False)
def garbageCollect():
    '''
    作品のない作者 や 作品のないタグ、 登録されていないタグの情報 などを削除する
    '''
    deleteArtistReq = '''DELETE FROM info_artist
    WHERE artistID NOT IN( SELECT DISTINCT artistID FROM data_illust)'''
    deleteTagDataReq = '''DELETE FROM data_tag
    WHERE illustID NOT IN( SELECT illustID FROM data_illust )'''
    deleteTagInfoReq = '''DELETE FROM info_tag
    WHERE tagID NOT IN( SELECT tagID FROM data_tag ) AND tagID != 42'''
    req = [deleteArtistReq, deleteTagDataReq, deleteTagInfoReq]
    for r in req:
        g.db.edit(r, autoCommit=False)
    g.db.commit()
    return {'status': 200, 'message': 'ok'}
