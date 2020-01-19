from bottle import run,route,response,request,static_file
from bottle import template,error
import sqlite3,json,math
from datetime import datetime

'''
 API: それぞれで検索
'''

def finder(sql,sql2):
    #usedID
    uid = request.query['id'] if "id" in request.query else "1"
    #pageID
    pid = request.query['p'] if "p" in request.query else "1"
    pid = int(pid) if pid.isdecimal() else 1
    #sortID
    sid = request.query['s'] if "s" in request.query else "0"
    #ソート用SQL追加(elseを使うため安全なはず)
    if sid == "1":
        sql += "illustDate DESC"
    elif sid == "2":
        sql += "illustLike"
    elif sid == "3":
        sql += "illustLike DESC"
    else:
        sql += "illustDate"
    #範囲指定用SQL追加(数値でなければ弾いてるため安全なはず)
    if pid == 1:
        pid = 0
    else:
        pid = ((pid-1)*12)-1
    sql += " LIMIT %s,%s"%(pid,12)
    datas = db.get(sql,[(uid)])
    img = db.get(sql2,[(uid)])[0]
    #返す
    ls = {"info":{"name":img[0],"count":int(img[1]),"pages":math.ceil(int(img[1])/12)},"imgs":[{"illustID":d[0], "title":d[1], "artistID":d[2], "artist":d[3], "date":d[4], "likeCount":d[5]} for d in datas]}
    return json.dumps(ls)

@route("/api/search/tag",method="GET")
def search_tag():
    result = finder("SELECT DISTINCT illustID,illustName,artistID,artistName,illustDate,illustLike FROM illust_main natural join info_artist natural join info_tag WHERE tagID = ? ORDER BY ","SELECT DISTINCT tagName,COUNT(tagID) FROM illust_tag natural join info_tag WHERE tagID = ? GROUP BY (tagID)")
    response.content_type = 'application/json'
    return result
    
@route("/api/search/artist",method="GET")
def search_artist():
    result = finder("SELECT DISTINCT illustID,illustName,artistID,artistName,illustDate,illustLike FROM illust_main natural join info_artist WHERE artistID = ? ORDER BY ","SELECT DISTINCT artistName,COUNT(artistID) FROM illust_main natural join info_artist WHERE artistID = ? GROUP BY (artistID)")
    response.content_type = 'application/json'
    return result
    
@route("/api/search/chara",method="GET")
def search_chara():
    result = finder("SELECT DISTINCT illustID,illustName,artistID,artistName,illustDate,illustLike FROM illust_main natural join info_artist natural join info_chara WHERE charaID = ? ORDER BY ","SELECT DISTINCT charaName,COUNT(charaID) FROM illust_main natural join info_chara WHERE charaID = ? GROUP BY (charaID)")
    response.content_type = 'application/json'
    return result
    
@route("/api/search/cross",method="GET")
def search_cross():
    #あとで実装する
    return "501"
    
'''
 API: イラストページ
'''    
@route("/api/illust")
def api_illust():
    iid = request.query['id'] if "id" in request.query else "1"
    #基本情報取得
    ndatas = db.get("SELECT illustID,illustName,artistID,artistName,illustDate,illustLike FROM illust_main natural join info_artist WHERE illustID = ?",[(iid)])
    if len(ndatas) == 1:
        ndatas = ndatas[0]
    else:
        return {}
    #タグ情報取得
    tdatas = db.get("SELECT tagID,tagName,nsfw FROM illust_tag natural join info_tag WHERE illustID = ?",[(iid)])
    #キャラ情報取得
    cdatas = db.get("SELECT charaID,charaName FROM illust_chara natural join info_chara WHERE illustID = ?",[(iid)])
    data = {
        "illustID":ndatas[0],
        "title":ndatas[1],
        "artistID":ndatas[2],
        "name":ndatas[3],
        "date":ndatas[4],
        "like":ndatas[5],
        "tag":[[t[0],t[1],t[2]] for t in tdatas],
        "chara":[[c[0],c[1]] for c in cdatas]
    }
    response.content_type = 'application/json'
    return json.dumps(data)
    
@route("/api/favorite",method="POST")
def api_favorite():
    iid = request.forms.iid
    db.edit("UPDATE illust_main SET illustLike = illustLike + 1 WHERE illustID = ?",[(iid)])
    return "200 OK"

'''
 API: 管理用API(公開ダメ)
'''   

@route("/admin_api/detect_illust",method="POST")
def sudo_detect_illust():
    return ""

@route("/admin_api/create_illust",method="POST")
def sudo_create_illust():
    '''
    {
        "title":"Test",
        "caption":"テストデータ",
        "artist":{
            //どれか1つが存在するかつあってればOK
            "twitterID":"適当でも",
            "pixivID":"適当でも",
            "name":"適当でも"
        },
        "tag":["","",""]
    }
    {
        "image":[
            <file>,
            <file>,
            <file>
        ]
    }
    '''
    #パラメータ確認
    if "title" not in request.json or "caption" not in request.json or "artist" not in request.json:
        return "Not Enough Items"
    illusts = request.forms.getall('image')
    for i in illusts:
        #TODO: ファイル拡張子変換対応
        if not i.filename.lower().endswith((".jpg",".jpeg")):
            return "Unsupported file"
    if "twitterID" not in request.json["artist"]\
    and "pixivID" not in request.json["artist"]\
    and "name" not in request.json["artist"]:
        return "Not Enough Items"
    #パラメータ整形
    if "twitterID" not in request.json["artist"]:
        request.json["artist"]["twitterID"] = "None"
    if "pixivID" not in request.json["artist"]:
        request.json["artist"]["pixivID"] = "None"
    if "name" not in request.json["artist"]:
        request.json["artist"]["name"] = "None"
    #作者情報取得
    illust_artist = request.json["artist"]
    if db.has("info_artist","artistName=? OR pixivID=? OR twitterID=?",
    [illust_artist["name"],illust_artist["pixivID"],illust_artist["twitterID"]]):
        db.edit("INSERT INTO info_artist (artistName,twitterID,pixivID) VALUES (?,?,?)",[illust_artist["name"],illust_artist["twitterID"],illust_artist["pixivID"]])
    artist_id = db.get("SELECT artistID FROM info_artist WHERE artistName=? OR pixivID=? or twitterID=?",[illust_artist["name"]])
    temp_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    #データ登録
    db.edit("INSERT INTO illust_main (illustDate,artistID,illustPage,illustName,illustDescription) VALUES (?,?,?,?,?)",[temp_date,artist_id,len(illusts),request.json["title"],request.json["caption"]])
    iid = str(db.get("SELECT max(illustID) FROM illust_main")[0][0])
    #画像保存
    for cnt,illust in enumerate(illusts):
        illust.save("%s-%s.jpg"%(iid,cnt))
    #タグ情報取得/作成
    for t in request.json["tag"]:
        if not db.has("info_tag","tagName=?",[t]):
            db.edit("INSERT INTO info_tag (tagName) VALUES (?)",[t])
        tid = db.get("SELECT tagID FROM info_tag WHERE tagName=?",[t])
        db.edit("INSERT INTO illust_tag (illustID,tagID) VALUES (?,?)",[iid,tid])
    return "OK"

@route("/admin_api/edit_illust",method="POST")
def sudo_edit_illust():
    if "type" not in request.json or "id" not in request.json or "data" not in request.json:
        return "Not Enough Items"
    #作品名変更
    if request.json["type"] == "name":
        column = "illustName"
    #作者ID変更
    elif request.json["type"] == "artist":
        column = "artistID"
    #説明文変更
    elif request.json["type"] == "caption":
        column = "illustDescription"
    #いいね数変更
    elif request.json["type"] == "like":
        column = "illustLike"
    else:
        return "Unknown Type"
    db.edit("UPDATE illust_main %s = ? WHERE illustID = ?"%(column),[request.json["data"],request.json["id"]])
    return "OK"
    

'''
 API: ユーザー
'''
    
@route("/login",method="POST")
def user_login():
    print(request.forms)

@route("/getSetting",method="GET")
def user_getSetting():
    pass

@route("/updateSetting",method="POST")
def user_updateSetting():
    pass

@route("/register",method="POST")
def user_register():
    pass

'''
 デフォルトレンダー
'''
@route('/<filename:path>')
def render_index(filename):
    return static_file(filename, root="./page/")
@route('/')
@route('')
def render_top():
    return static_file("index.html", root="./page/")    

if __name__ == "__main__":
    run(host="localhost", port=8080,reload=False)