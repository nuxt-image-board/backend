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
    "caption":"ã?ã¹ããã¼ã¿",
    "originUrl": "åURL",
    "originService": "å?ãµã¼ãã¹å?",
    "imageUrl": "ç»åã?®åURL",
    //ã©ãã1ã¤ãå­å¨ãããã¤ãã£ã¦ãã?°OK
    "artist":{
        "twitterID":"é©å½ã§ã?",
        "pixivID":"é©å½ã§ã?",
        "name":"é©å½ã§ã?"
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
        '''æ?å®ãµã¤ãºããã?ã®ç»åãä½ã(æ¢ã«æ?å®ãããµã¤ãºä»¥ä¸ã?®å ´åã?¯ãã?®ã¾ã¾è¿ã)'''
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
        # PNG/WEBPã«å¤æãã
        imgObj = Image.open(img_src).convert("RGB")
        return imgObj

    def createLarge(self):
        # 1280x960ããã?ã«ç¸®å°ãã?
        large = self.shrinkImage(self.orig,1280,960)
        return large

    def createSmall(self):
        # 640x480ããã?ã«ç¸®å°ãã?
        small = self.shrinkImage(self.orig,640,480)
        return small
        
    def createThumb(self, targetX=320, targetY=240):
        # ãµã?ãã¤ã«ãä½æ?ãã?
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
    # ããªã?ã¼ã·ã§ã³ã¯ã¨ã³ãã?ã¤ã³ãã§ã?ã£ã¦ã?ãåæ?
    # ã¤ã³ã¹ã¿ã³ã¹ä½æ??
    conn = SQLHandler()
    userID = str(params["userID"])
    uploadLogger = UploadLogger(conn, userID)
    # ãã©ã¡ã¼ã¿ãèª­ã¿åºã?
    artistName = params["artist"].get("name", None)
    pixivID = params["artist"].get("pixivID", None)
    twitterID = params["artist"].get("twitterID", None)
    illustName = params.get("title", "ç¡é¡?")
    illustDescription = params.get("caption", "ã³ã¡ã³ããªã?")
    illustPage = 1
    illustOriginUrl = params.get("originUrl", "https://gochiusa.com")
    illustOriginSite = params.get("originService", "ä¸æ??")
    illustNsfw = params.get("nsfw", "0")
    illustNsfw = "1" if illustNsfw not in [0,"0","False","false"] else "0"
    # åºå¸æç¹ã®éè¤?ç¢ºèª?
    resp = conn.get(
        "SELECT illustID FROM data_illust WHERE illustOriginUrl=%s AND illustOriginUrl <> 'https://gochiusa.com'",
        (illustOriginUrl,)
    )
    if resp:
        conn.rollback()
        uploadLogger.logDuplicatedImageError()
        return
    #æ¢å­ã?®ä½è??ã§ãªããã°æ°è¦ä½æ??
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
    #ä½è??IDãåå¾ãã?
    artistID = conn.get(
        "SELECT artistID FROM info_artist WHERE artistName=%s OR pixivID=%s or twitterID=%s",
        (artistName,pixivID,twitterID)
    )[0][0]
    #ãã©ã¡ã¼ã¿æç¹ã®ã?ã¼ã¿ç»é²
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
    # ç»é²ããç»åã?®IDãåå¾?
    illustID = conn.get("SELECT illustID FROM data_illust WHERE illustName=%s ORDER BY illustID DESC", (illustName,) )[0][0]
    #ã¿ã°æ?å ±åå¾?/ä½æ??
    #ã­ã£ã©æ?å ±åå¾?/ä½æ??
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
    # ç»åä¿å­å?¦ç?
    isConflict = False
    fileDir = "static/illusts/"
    try:
        with TemporaryDirectory() as tempFolder:
            fileOrigPath = os.path.join(tempFolder, f"{illustID}.raw")
            # ä½æç®ã®ç»åãä¿å­ãããã¯URLãã©ã¡ã¼ã¿ã§è¦ã
            page = 0
            if "?" in params["imageUrl"]\
            and "***REMOVED***" not in params["imageUrl"]\
            and "***REMOVED***" not in params["imageUrl"]:
                query = parse_query(params["imageUrl"][params["imageUrl"].find("?")+1:])
                page = int(query["page"][0]) - 1
            # ã?ã¤ã?ã¿ã¼ããåãå ´å?
            if params["imageUrl"].startswith("https://twitter.com/"):
                tg = TweetGetter()
                imgs = tg.getTweet(params["imageUrl"])['illust']['imgs']
                img_addr = imgs[page]["large_src"]
                tg.downloadIllust(img_addr, fileOrigPath)
            # Pixivããåãå ´å?
            elif params["imageUrl"].startswith("https://www.pixiv.net/"):
                ig = IllustGetter()
                imgs = ig.getIllust(params["imageUrl"])['illust']['imgs']
                img_addr = imgs[page]["large_src"]
                ig.downloadIllust(img_addr, fileOrigPath)
            # ã­ã¼ã«ã«ããåãå ´å?
            else:
                shutil.move(params["imageUrl"][params["imageUrl"].find("/static/temp/")+1:] ,fileOrigPath)
            # ç»åæç¹ã®éè¤?ç¢ºèª?
            hash = int(str(imagehash.phash(Image.open(fileOrigPath))), 16)
            is_match = conn.get(
                "SELECT illustID, illustName, data_illust.artistID, artistName, BIT_COUNT(illustHash ^ %s) AS SAME FROM `data_illust` INNER JOIN info_artist ON info_artist.artistID = data_illust.artistID HAVING SAME = 0",
                (hash,)
            )
            if is_match:
                isConflict = True
                raise Exception('Conflict')
            # Origã?ã¼ã¿ãç§»å?
            origType = what_img(fileOrigPath)
            if origType not in ["png","jpg","gif","webp"]:
                with open(fileOrigPath,"rb") as f:
                    file = f.read()
                    if file[:2] != b'\xff\xd8':
                        raise Exception('Unknown file')
                    else:
                        origType="jpg"
            shutil.move(fileOrigPath, fileOrigPath.replace("raw", origType))
            #ç»åå?¦ç?æç¹ã®ã?ã¼ã¿ç»é²
            resp = conn.edit(
                "UPDATE data_illust SET illustExtension = %s, illustHash = %s WHERE illustID = %s",
                (origType, hash, illustID),
                False
            )
            if not resp:
                conn.rollback()
                uploadLogger.logServerExplodedError()
                return
            #ç»åã?®å¤æ/ä¿å­å?¦ç?
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
        "caption":"ã?ã¹ããã¼ã¿",
        "originUrl": "åURL",
        "originService": "å?ãµã¼ãã¹å?",
        "imageUrl": "ç»åã?®åURL",
        "artist":{
            "name":"é©å½ã§ã?"
        },
        "tag":["ã?ã¹ã?"],
        "nsfw": 0
    }
    print("ok")
    conn = SQLHandler()
    uploadLogger = UploadLogger(conn, "3")
    print(uploadLogger.uploadID)
    #processConvertRequest(params)