from flask import Flask, g, request, jsonify, Blueprint
from .authorizator import auth, token_serializer
from .limiter import apiLimiter, handleApiPermission
from .recorder import recordApiRequest
import subprocess

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
    deleteTagInfoReq = '''SELECT * FROM info_tag
    WHERE tagID NOT IN( SELECT tagID FROM data_tag ) AND tagID != 42'''
    req = [deleteArtistReq, deleteTagDataReq, deleteTagInfoReq]
    for r in req:
        g.db.edit(r, autoCommit=False)
    g.db.commit()
    return {'status': 200, 'message': 'ok'}


@superuser_api.route('/start_deploy_from_github', methods=["POST"], strict_slashes=False)
def deployNewVersion():
    password = request.args.get('password', type=str, default="")
    if password != "200_OK":
        return "200 OK"
    params = request.get_json()
    if params["ref"] != "refs/heads/master":
        return "200 OK"
    # Gitの設定は予め済ませてある前提。
    # 参考: https://qiita.com/ego/items/3d23cda713f29f0dd141
    # https://mseeeen.msen.jp/git-sparse-checkout/
    # https://docs.python.org/ja/3/library/subprocess.html#subprocess.run
    subprocess.run(
        "git pull origin master".split(),
        cwd="/home/deploy",
        shell=True
    )
    # Pullしたデータを持ち込む
    subprocess.run(
        "chmod -R 770 *".split(),
        cwd="/home/deploy",
        shell=True
    )
    subprocess.run(
        "cp -R * /mnt/hdd1/Servers/Gochi_API".split(),
        cwd="/home/deploy",
        shell=True
    )
    # API再起動 (runだと応答が返せない)
    subprocess.Popen("systemctl restart usagi_api.service".split())
    return "200 OK"