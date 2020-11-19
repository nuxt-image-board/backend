## 手動での稼働の流れ
利用者がインストール時にすることのリスト

## 1 ソースのクローン
```
このリポジトリはサブモジュールを使っているので普通にzipで落とすと動きません
```
## 2 pipでパッケージを揃える
```
pip install -r requirements.txt
pip install -r ./api/scraper-lib/requirements.txt
```

## 3 nginxやApache2等のProxyPass/ProxyPassReverseの設定
```
各自で設定すること
```