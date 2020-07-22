from flask import Blueprint, g, request, jsonify, escape
from .authorizator import auth, token_serializer
from .limiter import apiLimiter, handleApiPermission
from .recorder import recordApiRequest
import requests

toymoney_api = Blueprint('toymoney_api', __name__)
TOYMONEY_ENDPOINT = "http://127.0.0.1:7070"


@toymoney_api.route(
    '/<path:text>',
    methods=["POST", "GET", "PUT"],
    strict_slashes=False
)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def torimochi(text):
    print(g.userID)
    toyApiKey = g.db.get(
        "SELECT userToyApiKey FROM data_user WHERE userID=%s",
        (g.userID,)
    )[0][0]
    headers = {"Authorization": f"Bearer {toyApiKey}"}
    path = request.path.replace("toymoney/", "")
    if request.method == "GET":
        resp = requests.get(
            TOYMONEY_ENDPOINT + path
            + '?' + request.query_string.decode("utf8"),
            headers=headers
        )
    else:
        data = request.get_json()
        if request.method == "POST":
            resp = requests.post(
                TOYMONEY_ENDPOINT + path,
                json=data,
                headers=headers
            )
        else:
            resp = requests.put(
                TOYMONEY_ENDPOINT + path,
                json=data,
                headers=headers
            )
    return (resp.text, resp.status_code, resp.headers.items())
