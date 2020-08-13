from flask import Blueprint, request, g, jsonify
from .authorizator import auth, token_serializer
from .limiter import apiLimiter, handleApiPermission
from .recorder import recordApiRequest

uploaders_api = Blueprint('uploaders_api', __name__)

#
# 投稿者(アカウント)関連。
# 編集や削除はaccountsAPIにあるため取得だけを実装
#


@uploaders_api.route('/<int:uploaderID>', methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def getUploader(uploaderID):
    recordApiRequest(g.userID, "getUploader", param1=uploaderID)
    uploaderData = g.db.get(
        "SELECT userID,userName,userFavorite FROM data_user WHERE userID = %s",
        (uploaderID,)
    )
    if len(uploaderData) < 1:
        return jsonify(status=404, message="Specified uploader was not found")
    uploaderData = uploaderData[0]
    return jsonify(status=200, data={
        "id": uploaderData[0],
        "name": uploaderData[1],
        "favorite": uploaderData[2]
    })
