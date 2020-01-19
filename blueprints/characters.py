from flask import Blueprint, request, g, jsonify
from .authorizator import auth,token_serializer
from .limiter import apiLimiter,handleApiPermission
from .recorder import recordApiRequest

characters_api = Blueprint('characters_api', __name__)

#
# キャラ関連
#

@characters_api.route('/',methods=["POST"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def addCharacter():
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    if "charaName" not in params.keys():
        return jsonify(status=400, message="Request parameters are not satisfied.")
    params = {p: g.validate(params[p]) for p in params.keys()}
    charaName = params.get('charaName')
    if g.db.has("info_chara","charaName=?",(charaName,)):
        return jsonify(status=409, message="The character is already exist.")
    charaDescription = params.get('charaDescription', None)
    charaBackground = params.get('charaBackground', None)
    charaIcon = params.get('charaIcon', None)
    charaBirthday = params.get('charaBirthday', None)
    resp = g.db.edit(
        "INSERT INTO `info_chara`(`charaName`,`charaDescription`,`charaBackground`,`charaIcon`,`charaBirthday`,`charaEndpoint`) VALUES (?,?,?,?,?,NULL)",
        (charaName, charaDescription, charaBackground, charaIcon, charaBirthday)
    )
    if resp:
        createdID = g.db.get(
            "SELECT charaID FROM info_chara WHERE charaName = ?",(charaName,)
        )[0][0]
        return jsonify(status=200, message="Created", charaID=createdID)
    else:
        return jsonify(status=500, message="Server bombed.")

@characters_api.route('/<int:charaID>',methods=["DELETE"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def removeCharacter(charaID):
    if not g.db.has("info_chara","charaID=?",(charaID,)):
        return jsonify(status=404, message="Specified character was not found")
    illustCount = g.db.get(
        "SELECT COUNT(charaID) FROM illust_main WHERE charaID = ?", (charaID,)
    )[0][0]
    if not illustCount:
        return jsonify(status=409, message="The character is locked by reference.")
    resp = g.db.edit("DELETE FROM info_chara WHERE charaID = ?", (charaID,))
    if resp:
        return jsonify(status=200, message="Delete succeed.")
    else:
        return jsonify(status=500, message="Server bombed.")
    
@characters_api.route('/<int:charaID>',methods=["GET"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def getCharacter(charaID):
    charaData = g.db.get(
        "SELECT * FROM info_chara WHERE charaID = ?", (charaID,)
    )
    if len(charaData) < 1:
        return jsonify(status=404, message="Specified character was not found")
    charaData = charaData[0]
    return jsonify(status=200, data={
        "id": charaData[0],
        "name": charaData[1],
        "description": charaData[2],
        "background": charaData[3],
        "icon": charaData[4],
        "birthday": charaData[5]
    })
    
@characters_api.route('/<int:charaID>',methods=["PUT"], strict_slashes=False)
@auth.login_required
@apiLimiter.limit(handleApiPermission)
def editCharacter(charaID):
    params = request.get_json()
    if not params:
        return jsonify(status=400, message="Request parameters are not satisfied.")
    validParams = [
        "charaName",
        "charaDescription",
        "charaIcon",
        "charaBirthday",
        "charaEndpoint"
    ]
    if len(params.keys() - validParams) == len(params.keys()):
        return jsonify(status=400, message="Request parameters are not satisfied.")
    params = {p:params[p] for p in params.keys() if p in validParams}
    for p in params.keys():
        resp = g.db.edit(
            "UPDATE `info_chara` SET `%s`=? WHERE charaID=?"%(p),
            (params[p],charaID,)
        )
        if not resp:
            return jsonify(status=500, message="Server bombed.")
    return jsonify(status=200, message="Update succeed.")