from flask import g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


# APIアクセス数制限
def handleApiPermission():
    '''
    権限0: 一般ユーザ用
    1-2 : 未使用
    権限3: 投稿Bot専用
    4   : 未使用
    権限5: アカウント登録/非ログイン状態用
    6-8 : 未使用
    権限9: フルアクセス
    '''
    permissionLimitDict = {
        0: "10/second",
        1: "10/second",
        2: "10/second",
        3: "20/second",
        4: "10/second",
        5: "30/second",
        6: "10/second",
        7: "10/second",
        8: "10/second",
        9: "1000/second"
    }
    if g.userPermission:
        if g.userPermission >= 0 and g.userPermission <= 9:
            return permissionLimitDict[g.userPermission]
    return "10/second"


limiter = Limiter(
    key_func=get_remote_address,
    headers_enabled=True,
    default_limits=[handleApiPermission]
)
