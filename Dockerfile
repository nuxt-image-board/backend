# Pythonイメージの取得
FROM python:3.8.6-slim-buster
# ワーキングディレクトリの指定
WORKDIR /usr/local/app
# モジュールを揃える
COPY . .
RUN pip install -r requirements.txt
RUN pip install -r blueprints/lib/requirements.txt
# 起動環境設定
EXPOSE 5000
ENTRYPOINT [ "gunicorn", "app:app" ]
CMD [ "-c", "gunicorn_config.py" ]