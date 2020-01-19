import sqlite3


class SQLHandler(object):
    def __init__(self,file_name="concept.db"):
        self.db = sqlite3.connect(file_name)
        self.conn = self.db.cursor()

    def get(self,sql,data=None):
        if data == None:
            self.conn.execute(sql)
        else:
            self.conn.execute(sql,data)
        return self.conn.fetchall()
        
    def edit(self,sql,data=None):
        try:
            if data == None:
                self.conn.execute(sql)
            else:
                self.conn.execute(sql,data)
            self.db.commit()
            return True
        except Exception as e:
            print(e)
            self.db.rollback()
            return False
            
    def has(self,tableName,condition,data=None):
        d = self.get("SELECT 'T' FROM %s WHERE %s"%(tableName,condition),data)
        if len(d) > 0:
            return True
        else:
            return False
            
    def close(self):
        self.conn.close()