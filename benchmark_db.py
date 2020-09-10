from db import SQLHandler
from statistics import mean
import time
db = SQLHandler(file_name="***REMOVED***")

sqls = [
    "SELECT illustID, data_illust.artistID, illustName, illustDescription, illustDate, illustPage, illustLike, illustOriginUrl, illustOriginSite, illustNsfw, artistName, illustExtension, illustStatus FROM data_illust, info_artist WHERE data_illust.illustStatus = 0 AND data_illust.artistID = info_artist.artistID ORDER BY data_illust.illustLike DESC LIMIT 20 OFFSET 40",
    "SELECT illustID, data_illust.artistID, illustName, illustDescription, illustDate, illustPage, illustLike, illustOriginUrl, illustOriginSite, illustNsfw, artistName, illustExtension, illustStatus FROM data_illust INNER JOIN info_artist ON data_illust.artistID = info_artist.artistID WHERE illustStatus = 0 ORDER BY illustLike DESC LIMIT 20 OFFSET 40",
    "SELECT T1.*, info_artist.artistName FROM(SELECT illustID, artistID, illustName, illustDescription, illustDate, illustPage, illustLike, illustOriginUrl, illustOriginSite, illustNsfw, illustExtension, illustStatus FROM data_illust WHERE illustStatus = 0 ORDER BY illustLike DESC LIMIT 20 OFFSET 40) AS T1 LEFT JOIN info_artist ON info_artist.artistID = T1.artistID"
]

for x, s in enumerate(sqls):
    pt = []
    for i in range(300):
        st = time.time()
        db.get(s)
        pt.append(time.time() - st)
    print(f"Total Time ({x+1}): {round(mean(pt),4)}s")
