from flask_caching import Cache

apiCache = Cache(config={'CACHE_TYPE': 'simple', 'CACHE_THRESHOLD': 100})
