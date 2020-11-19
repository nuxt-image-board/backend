## Dockerを使った稼働の流れ
利用者がインストール時にすることのリスト

### 1 dockerおよびdocker-composeの導入
ラズパイの場合は[こちらを参考に](https://qiita.com/k_ken/items/0f2d6af2618618982723)
```
curl -sSL https://get.docker.com | sh
sudo pip3 install docker-compose
```
Windowsの場合は[こちらを参考に](https://qiita.com/KoKeCross/items/a6365af2594a102a817b)
```
Windowsを2004以降のビルドにアップデート
PowerShellを管理者として開く
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux
Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform
再起動する
[WSL2をインストール](https://docs.microsoft.com/en-us/windows/wsl/wsl2-kernel)
[Ubuntuをインストール](https://www.microsoft.com/store/apps/9n6svws3rx71)
[Docker for Desktopをインストール](https://www.docker.com/products/docker-desktop)
```

## 2 コンテナを実行
```
.env_exampleを.envとしてdockerフォルダにコピー
(dockerフォルダ内に移動)
.envに必要なトークンなどを書き込む
docker-compose up
```

## 3 nginxやApache2等のProxyPass/ProxyPassReverseの設定
```
各自で設定すること
```