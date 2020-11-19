from flask import Flask, g, request, jsonify, Blueprint, current_app
from ..extensions.httpauth import auth
from ..extensions.limiter import limiter, handleApiPermission
from .recorder import recordApiRequest

mute_api = Blueprint('mute_api', __name__)


@mute_api.route('/add', methods=["POST"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def addMute():
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    if not params:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    muteTargetType = params.get("type", None)
    muteTargetId = params.get("id", None)
    if not muteTargetId or not muteTargetType:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    recordApiRequest(
        g.userID,
        "addMute",
        param1=muteTargetType,
        param2=muteTargetId
    )
    if g.db.has(
        "data_mute",
        "targetType=%s AND targetID=%s",
        (muteTargetType, muteTargetId)
    ):
        return jsonify(status=400, message="the mute is already exists.")
    resp = g.db.edit(
        "INSERT INTO data_mute (targetType, targetID, userID) "
        + "VALUES (%s,%s,%s)",
        (muteTargetType, muteTargetId, g.userID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Added")


@mute_api.route('/remove', methods=["POST"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def removeMute():
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    params = request.get_json()
    if not params:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    muteTargetType = params.get("type", None)
    muteTargetId = params.get("id", None)
    if not muteTargetId or not muteTargetType:
        return jsonify(
            status=400,
            message="Request parameters are not satisfied."
        )
    recordApiRequest(
        g.userID,
        "removeMute",
        param1=muteTargetType,
        param2=muteTargetId
    )
    if not g.db.has(
        "data_mute",
        "targetType=%s AND targetID=%s",
        (muteTargetType, muteTargetId)
    ):
        return jsonify(status=400, message="the mute was not found")
    resp = g.db.edit(
        "DELETE FROM data_mute"
        + " WHERE targetType=%s AND targetID=%s AND userID=%s",
        (muteTargetType, muteTargetId, g.userID)
    )
    if not resp:
        return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Removed")


@mute_api.route('/list', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def listMute():
    recordApiRequest(
        g.userID,
        "listMute",
        param1=g.userID
    )
    tagMute = g.db.get(
        "SELECT targetID FROM data_mute WHERE userID=%s AND targetType=1",
        (g.userID,)
    )
    artistMute = g.db.get(
        "SELECT targetID FROM data_mute WHERE userID=%s AND targetType=2",
        (g.userID,)
    )
    return jsonify(
        status=200,
        message="ok",
        data={
            "tag": [t[0] for t in tagMute],
            "artist": [a[0] for a in artistMute]
        }
    )
