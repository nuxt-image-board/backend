from flask import g
from flask_httpauth import HTTPTokenAuth
from itsdangerous import JSONWebSignatureSerializer as Serializer

auth = HTTPTokenAuth('Bearer')
token_serializer = Serializer("***REMOVED***")


@auth.verify_token
def verify_token(token):
    g.userID = None
    try:
        data = token_serializer.loads(token)
        # print(data)
    except:  # noqa: E722
        # print("VerifyFailed")
        return False
    if 'id' in data:
        g.userID = data['id']
        g.userApiSeq = data['seq']
        g.userApiKey = token
        g.userPermission = data['permission']
        if g.db.has(
            "data_user",
            "userID=%s AND userApiSeq=%s AND userPermission=%s",
            (g.userID, g.userApiSeq, g.userPermission)
        ):
            return True
    return False