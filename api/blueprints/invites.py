from flask import Blueprint, g, request, jsonify, escape
from ..extensions import auth, token_serializer
from ..extensions import limiter, handleApiPermission
from .recorder import recordApiRequest
from hashids import Hashids
from time import time

invites_api = Blueprint('invites_api', __name__)


@invites_api.route('/', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def createInvite():
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message="Bad request")
    if g.db.has(
        "data_invite",
        f"inviter = {g.userID} AND invitee IS NULL"
    ):
        return jsonify(status=400, message="Multiple invitation is not allowed for now.", data={})
    hash_gen = Hashids(salt="gochiusa_random", min_length=8)
    inviteCode = hash_gen.encode(int(time())+g.userID)
    resp = g.db.edit(
        "INSERT INTO data_invite (inviter, inviteCode) VALUES (%s, %s)",
        (g.userID, inviteCode),
        False
    )
    if not resp:
        return jsonify(status=409, message="Sorry, your request conflicted. Try again later.", data={})
    inviteID = g.db.get(
        "SELECT inviteID FROM data_invite WHERE inviter=%s AND inviteCode=%s",
        (g.userID, inviteCode)
    )[0][0]
    g.db.commit()
    return jsonify(status=200, message="ok", data={'code': inviteCode, 'id': inviteID})


@invites_api.route('/<int:inviteID>', methods=["DELETE"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def deleteInvite(inviteID):
    if g.userPermission != 9:
        resp = g.db.edit(
            "DELETE FROM data_invite WHERE inviter=%s AND inviteID=%s",
            (g.userID, inviteID)
        )
    else:
        resp = g.db.edit(
            "DELETE FROM data_invite WHERE inviteID=%s",
            (inviteID)
        )
    if not resp:
        return jsonify(status=500, message="server bombed")
    return jsonify(status=200, message="ok")


@invites_api.route('/<int:invitesID>', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def getInvite(invitesID):
    if g.userPermission != 9:
        return jsonify(status=401, message="not allowed")
    return "Not implemeted"


@invites_api.route('/list', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def listInvite(invitesID):
    if g.userPermission != 9:
        return jsonify(status=401, message="not allowed")
    return "Not implemeted"
