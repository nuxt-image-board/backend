from PIL import Image
from db import SQLHandler
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs as parse_query
from .lib.pixiv_client import IllustGetter
from .lib.twitter_client import TweetGetter
from imghdr import what as what_img
from PIL import Image
import os
import shutil
import imagehash
import traceback

''' 
REQ
{
    "title":"Test",
    "caption":"繝?繧ｹ繝医ョ繝ｼ繧ｿ",
    "originUrl": "蜈ザRL",
    "originService": "蜈?繧ｵ繝ｼ繝薙せ蜷?",
    "imageUrl": "逕ｻ蜒上?ｮ蜈ザRL",
    //縺ｩ繧後°1縺､縺悟ｭ伜惠縺吶ｋ縺九▽縺ゅ▲縺ｦ繧後?ｰOK
    "artist":{
        "twitterID":"驕ｩ蠖薙〒繧?",
        "pixivID":"驕ｩ蠖薙〒繧?",
        "name":"驕ｩ蠖薙〒繧?"
    },
    "tag":["","",""],
    "chara": ["","",""],
    "nsfw": 0
}
'''

class UploadImageProcessor():
    def __init__(self, img_src):
        self.orig = self.createOrig(img_src)

    def shrinkImage(self, imgObj, targetX=640, targetY=480):
        '''謖?螳壹し繧､繧ｺ縺舌ｉ縺?縺ｮ逕ｻ蜒上ｒ菴懊ｋ(譌｢縺ｫ謖?螳壹＠縺溘し繧､繧ｺ莉･荳九?ｮ蝣ｴ蜷医?ｯ縺昴?ｮ縺ｾ縺ｾ霑斐☆)'''
        x, y = imgObj.size
        if x <= targetX and y <= targetY:
            return imgObj
        if x > targetX:
            new_x = targetX
            hiritsu_x = new_x / x
            new_y = int(y * hiritsu_x)
            resp = imgObj.resize((new_x,new_y), Image.LANCZOS)
            return resp
        else:
            new_y = targetY
            hiritsu_y = new_y / y
            new_x = int(x * hiritsu_y)
            resp = imgObj.resize((new_x,new_y), Image.LANCZOS)
            return resp
            
    def createOrig(self, img_src):
        # PNG/WEBP縺ｫ螟画鋤縺吶ｋ
        imgObj = Image.open(img_src).convert("RGB")
        return imgObj

    def createLarge(self):
        # 1280x960縺舌ｉ縺?縺ｫ邵ｮ蟆上☆繧?
        large = self.shrinkImage(self.orig,1280,960)
        return large

    def createSmall(self):
        # 640x480縺舌ｉ縺?縺ｫ邵ｮ蟆上☆繧?
        small = self.shrinkImage(self.orig,640,480)
        return small
        
    def createThumb(self, targetX=320, targetY=240):
        # 繧ｵ繝?繝阪う繝ｫ繧剃ｽ懈?舌☆繧?
        x, y = self.orig.size
        thumbnail = Image.new(
            "RGB",
            (targetX, targetY),
            (255, 0, 0, 0)
        )
        new_y = targetY
        hiritsu_y = new_y / y
        new_x = int(x * hiritsu_y)
        cropped = self.orig.resize((new_x,new_y), Image.LANCZOS)
        thumbnail.paste(cropped, ((targetX-new_x)//2,0))
        return thumbnail

class UploadLogger():
    def __init__(self, conn, userID):
        self.conn = conn
        self.uploadID = self.getUploadID(userID)

    def getUploadID(self, userID):
        resp = self.conn.edit(
            "INSERT INTO data_upload (uploadStatus,userID) VALUES (1, %s)",
            (userID,)
        )
        if not resp:
            self.conn.rollback()
            return ValueError('DB exploded')
        uploadID = self.conn.get(
            "SELECT MAX(uploadID) FROM data_upload WHERE userID=%s",
            (userID,)
        )
        if not uploadID:
            self.conn.rollback()
            return ValueError('DB exploded')
        return uploadID[0][0]

    def logStatus(self, status):
        resp = self.conn.edit(
            "UPDATE data_upload SET uploadStatus = %s WHERE uploadID = %s",
            (status, self.uploadID,),
            False
        )
        if not resp:
            self.conn.rollback()
            return ValueError('DB exploded')
        return True

    def logConvertedThumb(self):
        self.logStatus(2)
        self.conn.commit()
        return True

    def logConvertedSmall(self):
        self.logStatus(3)
        self.conn.commit()
        return True

    def logConvertedLarge(self):
        self.logStatus(4)
        self.conn.commit()
        return True

    def logCompleted(self, illustID):
        resp = self.conn.edit(
            "UPDATE data_upload SET uploadStatus = 5, uploadFinishedDate = NOW(), illustID=%s WHERE uploadID = %s",
            (self.uploadID, illustID),
            False
        )
        if not resp:
            self.conn.rollback()
            return ValueError('DB exploded')
        self.conn.commit()
        return True

    def logDuplicatedImageError(self):
        self.logStatus(8)
        self.conn.commit()
        return True

    def logServerExplodedError(self):
        self.logStatus(9)
        self.conn.commit()
        return True

def processConvertRequest(params):
    # 繝舌Μ繝?繝ｼ繧ｷ繝ｧ繝ｳ縺ｯ繧ｨ繝ｳ繝峨?昴う繝ｳ繝医〒繧?縺｣縺ｦ縺?繧句燕謠?
    # 繧､繝ｳ繧ｹ繧ｿ繝ｳ繧ｹ菴懈??
    conn = SQLHandler()
    userID = str(params["userID"])
    uploadLogger = UploadLogger(conn, userID)
    # 繝代Λ繝｡繝ｼ繧ｿ繧定ｪｭ縺ｿ蜃ｺ縺?
    artistName = params["artist"].get("name", None)
    pixivID = params["artist"].get("pixivID", None)
    twitterID = params["artist"].get("twitterID", None)
    illustName = params.get("title", "辟｡鬘?")
    illustDescription = params.get("caption", "繧ｳ繝｡繝ｳ繝医↑縺?")
    illustPage = 1
    illustOriginUrl = params.get("originUrl", "https://gochiusa.com")
    illustOriginSite = params.get("originService", "荳肴??")
    illustNsfw = params.get("nsfw", "0")
    illustNsfw = "1" if illustNsfw not in [0,"0","False","false"] else "0"
    # 蜃ｺ蜈ｸ譎らせ縺ｮ驥崎､?遒ｺ隱?
    resp = conn.get(
        "SELECT illustID FROM data_illust WHERE illustOriginUrl=%s AND illustOriginUrl <> 'https://gochiusa.com'",
        (illustOriginUrl,)
    )
    if resp:
        conn.rollback()
        uploadLogger.logDuplicatedImageError()
        return
    #譌｢蟄倥?ｮ菴懆??縺ｧ縺ｪ縺代ｌ縺ｰ譁ｰ隕丈ｽ懈??
    if not conn.has(
        "info_artist",
        "artistName=%s OR pixivID=%s OR twitterID=%s",
        (artistName,pixivID,twitterID)
    ):
        resp = conn.edit(
            "INSERT INTO info_artist (artistName,twitterID,pixivID) VALUES (%s,%s,%s)",
            (artistName,pixivID,twitterID),
            False
        )
        if not resp:
            conn.rollback()
            uploadLogger.logServerExplodedError()
            conn.commit()
            return
    #菴懆??ID繧貞叙蠕励☆繧?
    artistID = conn.get(
        "SELECT artistID FROM info_artist WHERE artistName=%s OR pixivID=%s or twitterID=%s",
        (artistName,pixivID,twitterID)
    )[0][0]
    #繝代Λ繝｡繝ｼ繧ｿ譎らせ縺ｮ繝?繝ｼ繧ｿ逋ｻ骭ｲ
    resp = conn.edit(
        "INSERT INTO data_illust (artistID,illustName,illustDescription,illustPage,illustOriginUrl,illustOriginSite,userID,illustNsfw) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            str(artistID),
            illustName,
            illustDescription,
            illustPage,
            illustOriginUrl,
            illustOriginSite,
            userID,
            illustNsfw
        ),
        False
    )
    if not resp:
        conn.rollback()
        uploadLogger.logServerExplodedError()
        return
    # 逋ｻ骭ｲ縺励◆逕ｻ蜒上?ｮID繧貞叙蠕?
    illustID = conn.get("SELECT illustID FROM data_illust WHERE illustName=%s ORDER BY illustID DESC", (illustName,) )[0][0]
    #繧ｿ繧ｰ諠?蝣ｱ蜿門ｾ?/菴懈??
    #繧ｭ繝｣繝ｩ諠?蝣ｱ蜿門ｾ?/菴懈??
    for i,k in enumerate(["tag", "chara"]):
        if k in params.keys():
            for t in params[k]:
                if not conn.has("info_tag","tagName=%s", (t,)):
                    conn.edit("INSERT INTO info_tag (userID,tagName,tagType,tagNsfw) VALUES (%s,%s,%s,0)", (userID,t,i), False)
                tagID = conn.get("SELECT tagID FROM info_tag WHERE tagName=%s",(t,))[0][0]
                resp = conn.edit("INSERT INTO data_tag (illustID,tagID) VALUES (%s,%s)",(str(illustID),str(tagID)), False)
                if not resp:
                    conn.rollback()
                    uploadLogger.logServerExplodedError()
                    return
    # 逕ｻ蜒丈ｿ晏ｭ伜?ｦ逅?
    isConflict = False
    fileDir = "static/illusts/"
    try:
        with TemporaryDirectory() as tempFolder:
            fileOrigPath = os.path.join(tempFolder, f"{illustID}.raw")
            # 菴墓椢逶ｮ縺ｮ逕ｻ蜒上ｒ菫晏ｭ倥☆繧九°縺ｯURL繝代Λ繝｡繝ｼ繧ｿ縺ｧ隕九ｋ
            page = 0
            if "?" in params["imageUrl"]\
            and "***REMOVED***" not in params["imageUrl"]\
            and "***REMOVED***" not in params["imageUrl"]:
                query = parse_query(params["imageUrl"][params["imageUrl"].find("?")+1:])
                page = int(query["page"][0]) - 1
            # 繝?繧､繝?繧ｿ繝ｼ縺九ｉ蜿悶ｋ蝣ｴ蜷?
            if params["imageUrl"].startswith("https://twitter.com/"):
                tg = TweetGetter()
                imgs = tg.getTweet(params["imageUrl"])['illust']['imgs']
                img_addr = imgs[page]["large_src"]
                tg.downloadIllust(img_addr, fileOrigPath)
            # Pixiv縺九ｉ蜿悶ｋ蝣ｴ蜷?
            elif params["imageUrl"].startswith("https://www.pixiv.net/"):
                ig = IllustGetter()
                imgs = ig.getIllust(params["imageUrl"])['illust']['imgs']
                img_addr = imgs[page]["large_src"]
                ig.downloadIllust(img_addr, fileOrigPath)
            # 繝ｭ繝ｼ繧ｫ繝ｫ縺九ｉ蜿悶ｋ蝣ｴ蜷?
            else:
                shutil.move(params["imageUrl"][params["imageUrl"].find("/static/temp/")+1:] ,fileOrigPath)
            # 逕ｻ蜒乗凾轤ｹ縺ｮ驥崎､?遒ｺ隱?
            hash = int(str(imagehash.phash(Image.open(fileOrigPath))), 16)
            is_match = conn.get(
                "SELECT illustID, illustName, data_illust.artistID, artistName, BIT_COUNT(illustHash ^ %s) AS SAME FROM `data_illust` INNER JOIN info_artist ON info_artist.artistID = data_illust.artistID HAVING SAME = 0",
                (hash,)
            )
            if is_match:
                isConflict = True
                raise Exception('Conflict')
            # Orig繝?繝ｼ繧ｿ繧堤ｧｻ蜍?
            origType = what_img(fileOrigPath)
            if origType not in ["png","jpg","gif","webp"]:
                with open(fileOrigPath,"rb") as f:
                    file = f.read()
                    if file[:2] != b'\xff\xd8':
                        raise Exception('Unknown file')
                    else:
                        origType="jpg"
            shutil.move(fileOrigPath, fileOrigPath.replace("raw", origType))
            #逕ｻ蜒丞?ｦ逅?譎らせ縺ｮ繝?繝ｼ繧ｿ逋ｻ骭ｲ
            resp = conn.edit(
                "UPDATE data_illust SET illustExtension = %s, illustHash = %s WHERE illustID = %s",
                (origType, hash, illustID),
                False
            )
            if not resp:
                conn.rollback()
                uploadLogger.logServerExplodedError()
                return
            #逕ｻ蜒上?ｮ螟画鋤/菫晏ｭ伜?ｦ逅?
            uploadConverter = UploadImageProcessor(fileOrigPath.replace("raw", origType))
            converts = {
                "thumb": [ uploadConverter.createThumb, uploadLogger.logConvertedThumb ],
                "small": [ uploadConverter.createSmall, uploadLogger.logConvertedSmall ],
                "large": [ uploadConverter.createLarge, uploadLogger.logConvertedLarge ]
            }
            for c in converts.keys():
                dir = os.path.join(fileDir, c)
                img = converts[c][0]()
                for e in ["jpg","webp"]:
                    img.save(
                        os.path.join(dir, f"{illustID}.{e}"),
                        quality=80
                    )
                converts[c][1]()
    except Exception as e:
        print(e)
        for folder in ["orig","thumb","small","large"]:
            dir = os.path.join(fileDir, folder)
            for extension in ["png","jpg","webp","gif"]:
                filePath = os.path.join(dir, f"{illustID}.{extension}")
                if os.path.exists(filePath):
                    os.remove(filePath)
        conn.rollback()
        if isConflict:
            uploadLogger.logDuplicatedImageError()
        else:
            uploadLogger.logServerExplodedError()
        return
    conn.commit()
    uploadLogger.logCompleted(illustID)
    return

if __name__ == "__main__":
    params = {
        "title":"Test",
        "caption":"繝?繧ｹ繝医ョ繝ｼ繧ｿ",
        "originUrl": "蜈ザRL",
        "originService": "蜈?繧ｵ繝ｼ繝薙せ蜷?",
        "imageUrl": "逕ｻ蜒上?ｮ蜈ザRL",
        "artist":{
            "name":"驕ｩ蠖薙〒繧?"
        },
        "tag":["繝?繧ｹ繝?"],
        "nsfw": 0
    }
    print("ok")
    conn = SQLHandler()
    uploadLogger = UploadLogger(conn, "3")
    print(uploadLogger.uploadID)
    #processConvertRequest(params)