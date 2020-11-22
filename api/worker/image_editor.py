from PIL import Image
from imagehash import phash


class UploadImageEditor():
    def setImageSource(self, img_src):
        self.orig = self.createOrig(img_src)

    def shrinkImage(self, imgObj, targetX=640, targetY=480):
        '''指定サイズぐらいの画像を作る(既に指定したサイズ以下の場合はそのまま返す)'''
        x, y = imgObj.size
        if x <= targetX and y <= targetY:
            return imgObj
        if x > targetX:
            new_x = targetX
            hiritsu_x = new_x / x
            new_y = int(y * hiritsu_x)
            resp = imgObj.resize((new_x, new_y), Image.LANCZOS)
            return resp
        else:
            new_y = targetY
            hiritsu_y = new_y / y
            new_x = int(x * hiritsu_y)
            resp = imgObj.resize((new_x, new_y), Image.LANCZOS)
            return resp

    def getImageSize(self):
        h, w = self.orig.size
        return h, w

    def getImageHash(self):
        return int(str(phash(self.orig)), 16)

    def getImageExtension(self):
        return self.orig.format.lower().replace("jpeg", "jpg")

    def createOrig(self, img_src):
        # PNG/WEBPに変換する
        imgObj = Image.open(img_src).convert("RGB")
        return imgObj

    def createLarge(self):
        # 1280x960ぐらいに縮小する
        large = self.shrinkImage(self.orig, 1280, 960)
        return large

    def createSmall(self):
        # 640x480ぐらいに縮小する
        small = self.shrinkImage(self.orig, 640, 480)
        return small

    def createThumb(self, targetX=320, targetY=240):
        # サムネイルを作成する
        x, y = self.orig.size
        thumbnail = Image.new(
            "RGB",
            (targetX, targetY),
            (255, 255, 255)
        )
        new_y = targetY
        hiritsu_y = new_y / y
        new_x = int(x * hiritsu_y)
        cropped = self.orig.resize((new_x, new_y), Image.LANCZOS)
        thumbnail.paste(cropped, ((targetX-new_x)//2, 0))
        return thumbnail
