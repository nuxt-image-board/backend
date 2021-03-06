from flask import Blueprint, g, request, jsonify
from ..extensions import (
    auth, limiter, handleApiPermission, record
)


report_api = Blueprint('report_api', __name__)


@report_api.route('/art/<int:artID>', methods=["POST"], strict_slashes=False)
def reportArt(artID):
    return "Not implemeted"


@report_api.route('/tag/<int:tagID>', methods=["POST"], strict_slashes=False)
def reportTag(tagID):
    return "Not implemeted"


@report_api.route('/user/<int:userID>', methods=["POST"], strict_slashes=False)
def reportUser(userID):
    return "Not implemeted"
