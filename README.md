## API
ごちイラのバックグラウンドサイド(Flask)

## Docker用ビルドの流れ
### 1 AMD64用のモジュール集イメージをビルドしてプッシュ(依存モジュール追加時)
```
docker build -t ghcr.io/gochiira/main-backend-depends:amd64 --file Dockerfile_require .  
docker tag a64ebdd234ce ghcr.io/gochiira/main-backend-depends:amd64  
docker push ghcr.io/gochiira/main-backend-depends:amd64
```
### 2 ARMv7用のモジュール集イメージをビルドしてプッシュ(依存モジュール追加時)
```
docker buildx build --platform linux/arm/v7 -t gochiira/main-backend-depends:armv7 --file Dockerfile_require .  
docker tag a64ebdd123ce ghcr.io/gochiira/main-backend-depends:armv7  
docker push ghcr.io/gochiira/main-backend-depends:armv7
```
### 3 git releaseブランチに対してプッシュ
github actionsが [ghcr.io/gochiira/gochiira-backend:amd64](https://github.com/orgs/gochiira/packages/container/package/gochiira-backend) [ghcr.io/gochiira/gochiira-backend:armv7](https://github.com/orgs/gochiira/packages/container/package/gochiira-backend) などでイメージを公開する