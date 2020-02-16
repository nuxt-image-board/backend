from PIL import Image

def shrinkImage(imgObj, targetX=640, targetY=480):
    '''指定サイズぐらいの画像を作る(既に指定したサイズ以下の場合はそのまま返す)'''
    x, y = imgObj.size
    if x <= targetX and y <= targetY:
        return imgObj
    if x > targetX:
        new_x = targetX
        hiritsu_x = new_x / x
        new_y = int(y * hiritsu_x)
        return imgObj.resize((new_x,new_y))
    else:
        new_y = targetY
        hiritsu_y = new_y / y
        new_x = int(x * hiritsu_y)
        return imgObj.resize((new_x,new_y))
        
def createLarge(imgObj):
    # 1280x960ぐらいに縮小する
    return shrinkImage(imgObj,1280,960)

def createSmall(imgObj):
    # 640x480ぐらいに縮小する
    return shrinkImage(imgObj,640,480)
    
def createThumb(imgObj, targetX=320, targetY=240):
    '''指定されたサイズのサムネイルを作る
    (縦長の場合は中央に置いて残りは透明色で埋める)'''
    x, y = imgObj.size
    thumbnail = Image.new(
        "RGBA",
        (targetX, targetY),
        (255, 0, 0, 0)
    )
    new_y = targetY
    hiritsu_y = new_y / y
    new_x = int(x * hiritsu_y)
    imgObj = imgObj.resize((new_x,new_y))
    thumbnail.paste(imgObj, ((targetX-new_x)//2,0))
    return thumbnail

if __name__ == "__main__":
    img = Image.open("tatenaga.jpg")
    large = createLarge(img)
    small = createSmall(img)
    thumb = createThumb(img)
    for extension in ["PNG","WEBP"]:
        large.save('large.'+extension.lower(), extension)
        small.save('small.'+extension.lower(), extension)
        thumb.save('thumb.'+extension.lower(), extension)