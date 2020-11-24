from flask import Blueprint, g, request, jsonify, current_app
from ..extensions import (
    auth, limiter, handleApiPermission, record
)
from tempfile import TemporaryDirectory
from base64 import b64encode
from uuid import uuid4
import os.path
import shutil
from imghdr import what as what_img
from imghdr import tests
from os import environ
from dotenv import load_dotenv

# .env読み込み
load_dotenv(verbose=True, override=True)

CDN_ADDRESS = f"{environ.get('API_OWN_ADDRESS')}/static/temp/"

ALLOWED_EXTENSIONS = ["gif", "png", "jpg", "jpeg", "webp"]
JPEG_MARK = b'\xff\xd8\xff\xdb\x00C\x00\x08\x06\x06' \
    b'\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f'


def test_jpeg(h, f):
    """JPEG data in JFIF format"""
    if b'JFIF' in h[:23]:
        return 'jpeg'
    """JPEG with small header"""
    if len(h) >= 32 and 67 == h[5] and h[:32] == JPEG_MARK:
        return 'jpeg'
    """JPEG data in JFIF or Exif format"""
    if h[6:10] in (b'JFIF', b'Exif') or h[:2] == b'\xff\xd8':
        return 'jpeg'


tests.append(test_jpeg)


def isNotAllowedFile(filename):
    if filename == ""\
        or '.' not in filename\
        or (filename.rsplit('.', 1)[1].lower()
            not in ALLOWED_EXTENSIONS):
        return True
    return False


scrape_api = Blueprint('scrape_api', __name__)


@scrape_api.route('/self', methods=["POST"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def getArtBySelf():
    if g.userPermission not in [0, 9]:
        return jsonify(status=400, message='Bad request')
    # これだけアップロードか何か、エンドポイント変えたほうがいいような気がする...
    if "file" not in request.files:
        return jsonify(status=400, message="File must be included")
    file = request.files['file']
    # ファイル拡張子確認
    if isNotAllowedFile(file.filename):
        return jsonify(status=400, message="The file is not allowed")
    with TemporaryDirectory() as temp_path:
        # 画像を一旦保存して確認
        uniqueID = str(uuid4()).replace("-", "")
        uniqueID = b64encode(uniqueID.encode("utf8")).decode("utf8")[:-1]
        tempPath = os.path.join(temp_path, uniqueID)
        file.save(tempPath)
        fileExt = what_img(tempPath)
        if not fileExt:
            return jsonify(status=400, message="The file is not allowed")
        # 大丈夫そうなので保存
        filePath = os.path.join(
            'static/temp',
            uniqueID + ".raw"
        )
        shutil.copy2(tempPath, filePath)
    return jsonify(
        status=200,
        message="ok",
        data={
            "url": CDN_ADDRESS + uniqueID + ".raw"
        }
    )


@scrape_api.route('/predict_tag', methods=["GET"], strict_slashes=False)
@auth.login_required
@limiter.limit(handleApiPermission)
def predictTag():
    return "Not implemeted"
