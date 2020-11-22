from itsdangerous import JSONWebSignatureSerializer
from time import time
from hashids import Hashids
import mysql.connector
import requests
import hashlib
from dotenv import load_dotenv
from os import environ
load_dotenv(verbose=True, override=True)


def getUserInput(variable_name, default=None):
    user_input = input("Input {variable_name} (Default: {default})>>")
    if user_input == "":
        return default
    else:
        return user_input


class NuxtImageBoardSetup():
    TOYMONEY_PASSWORD_HEAD = environ.get('TOYMONEY_PASSWORD_HEAD')
    TOYMONEY_ENDPOINT = environ.get('TOYMONEY_ENDPOINT')
    SALT_INVITE = environ.get('SALT_INVITE')
    SALT_PASS = environ.get('SALT_PASS')
    SALT_JWT = environ.get('SALT_JWT')

    def __init__(self, host, port, user, password, database, headless=False):
        self.conn = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        self.cursor = self.conn.cursor()
        if headless:
            self.createDatabase()
            self.createMainApiUser(self.createSubApiUser())

    def createDatabase(self):
        with open("init.sql", "r", encoding="utf8") as f:
            self.cursor.execute(f.read())
        self.cursor.commit()
        return True

    def createSubApiUser(self, display_id="nib_admin"):
        toyApiResp = requests.post(
            f"{self.TOYMONEY_ENDPOINT}/users/create",
            json={
                "name": display_id,
                "password": f"{self.TOYMONEY_PASSWORD_HEAD}{display_id}"
            }
        )
        if toyApiResp.status_code != 200:
            raise Exception("ToyMoneyへのリクエストに失敗しました")
        return toyApiResp.json()["apiKey"]

    def generateApiKey(self, accountID):
        self.cursor.execute(
            "SELECT userApiSeq,userPermission FROM data_user WHERE userID=%s",
            (accountID,)
        )
        apiSeq, apiPermission = self.cursor.fetchall()[0]
        serializer = JSONWebSignatureSerializer(self.SALT_JWT)
        token = serializer.dumps({
            'id': accountID,
            'seq': apiSeq + 1,
            'permission': apiPermission
        }).decode('utf-8')
        self.cursor.execute(
            """UPDATE data_user SET userApiSeq=userApiSeq+1, userApiKey=%s
            WHERE userID=%s""",
            (token, accountID)
        )
        self.cursor.commit()
        return token

    def createMainApiUser(
        self,
        toyapi_key,
        display_id="nib_admin",
        username="nib_admin",
        password="nib_admin",
        permission=9
    ):
        # パスワードをハッシュ化
        password = self.SALT_PASS+password
        password = hashlib.sha256(password.encode("utf8")).hexdigest()
        # ユーザーを追加
        self.cursor.execute(
            """INSERT INTO data_user
            (userDisplayID, userName, userPassword,
            userToyApiKey, userApiPermission)
            VALUES (%s,%s,%s,%s,%s)""",
            (display_id, username, password, toyapi_key, permission)
        )
        # ユーザー内部IDを取得
        self.cursor.execute(
            """SELECT userID FROM data_user
            WHERE userDisplayID=%s AND userPassword=%s""",
            (display_id, password)
        )
        user_id = self.cursor.fetchall()[0][0]
        # APIキーの作成
        api_key = self.generateApiKey(user_id)
        # マイリストの作成
        self.cursor.execute(
            """INSERT INTO info_mylist
            (mylistName, mylistDescription, userID)
            VALUES (%s,%s,%s)""",
            (f"{username}のマイリスト", "", user_id)
        )
        self.cursor.commit()
        return user_id, api_key

    def createInvitation(self, user_id, invite_code="RANDOM", code_count=1):
        invite_codes = []
        for _ in range(code_count):
            if invite_code == "RANDOM":
                hash_gen = Hashids(salt=self.SALT_INVITE, min_length=8)
                code = hash_gen.encode(int(time()) + user_id)
            else:
                code = invite_code
            invite_codes.append(code)
            self.cursor.execute(
                """INSERT INTO data_invite
                (inviter, inviteCode) VALUES (%s, %s)""",
                (user_id, code)
            )
        self.conn.commit()
        return invite_codes


if __name__ == "__main__":
    print("Welcome to NuxtImageBoard Setup wizard!")
    db_host = getUserInput("database host", "localhost")
    db_port = getUserInput("database port", 3306)
    db_user = getUserInput("database user", "nuxt_image_board")
    db_pass = getUserInput("database pass", "nuxt_image_board")
    db_name = getUserInput("database name", "nuxt_image_board")
    cl = NuxtImageBoardSetup(db_host, db_port, db_user, db_pass, db_name)
    while True:
        print("""実行したい操作を入力してください
            1: データベース作成
            2: ユーザー作成
            3: 招待コード作成
            4: 終了""")
        op_type = 0
        while op_type not in [1, 2, 3, 4]:
            op_number = getUserInput("operation number", "1")
            if not op_number.isdecimal():
                print("Please input number.")
            elif int(op_number) not in [1, 2, 3, 4]:
                print("Invalid operation number.")
            else:
                op_type = int(op_number)
        if op_type == 1:
            print("Creating database...")
            cl.createDatabase()
            print("Create database success!")
        elif op_type == 2:
            print("Creating user...")
            display_id = input("display id", "nib_admin")
            username = input("username", "nib_admin")
            password = input("password", "nib_admin")
            permission = input("permission", "9")
            toyapi_key = cl.createSubApiUser(display_id)
            user_id, api_key = cl.createMainApiUser(
                toyapi_key,
                display_id,
                username,
                password,
                permission
            )
            print("Create user success!")
            print(f"User id: {user_id}")
            print(f"Api key: {api_key}")
        elif op_type == 3:
            print("Creating invite...")
            user_id = input("user id", "1")
            invite_code = input("invite code", "RANDOM")
            code_count = input("code count", "1")
            codes = cl.createInvitation(
                user_id,
                invite_code,
                code_count
            )
            print("Create invite success!")
            print("Invite codes:")
            print("".join(codes))
        else:
            print("Bye")
            break
