# Pythonイメージの取得
FROM python:3.8.6-slim-buster
# ワーキングディレクトリの指定
WORKDIR /usr/local/app
# 環境依存でビルドできない場合がある
RUN apt-get update && apt-get install -y\
    build-essential \
    gfortran \
    python3-dev
# モジュールを揃える
COPY . .
RUN pip install -r requirements.txt
RUN pip install -r blueprints/lib/requirements.txt
# 不要になったものを削除
RUN apt-get clean && rm -rf /var/lib/apt/lists/*
# 起動環境設定
EXPOSE 5000
ENTRYPOINT [ "gunicorn", "app:app" ]
CMD [ "-c", "gunicorn_config.py" ]