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
        self.conn.edit(
            """UPDATE data_upload
            SET uploadStatus = 5, uploadFinishedDate = NOW(), illustID=%s
            WHERE uploadID = %s""",
            (illustID, self.uploadID)
        )
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
