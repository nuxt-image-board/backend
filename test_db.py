from db import SQLHandler
from datetime import datetime, timedelta
db = SQLHandler(file_name="***REMOVED***")

now = datetime.now()

for i in range(0, 100):
    old_date = datetime.now() - timedelta(days=i)
    resp = db.edit(
        """INSERT INTO data_ranking
        (rankingMonth, rankingDay, rankingWeek, rankingDayOfWeek)
        VALUES
        ({old_date.month},{old_date.day},{old_date.},{old_date.day})"""
    )
    if not resp:
        raise Exception("Value Error")