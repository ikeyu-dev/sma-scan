#!/bin/bash

# スマスキャン - HTTPS証明書セットアップスクリプト
# mkcertを使用してローカル開発用の証明書を生成する

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CERTS_DIR="$PROJECT_DIR/certs"

echo "=== スマスキャン 証明書セットアップ ==="
echo ""

# mkcertがインストールされているか確認
if ! command -v mkcert &> /dev/null; then
    echo "エラー: mkcertがインストールされていません"
    echo ""
    echo "以下のコマンドでインストールしてください:"
    echo ""
    echo "  macOS:   brew install mkcert"
    echo "  Linux:   apt install mkcert または yay -S mkcert"
    echo "  Windows: choco install mkcert"
    echo ""
    exit 1
fi

# 証明書ディレクトリを作成
mkdir -p "$CERTS_DIR"

# ローカルCAをインストール（初回のみ）
echo "ローカルCAをインストール中..."
mkcert -install

# 現在のPCのIPアドレスを取得
get_local_ip() {
    case "$(uname -s)" in
        Darwin)
            ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "192.168.1.100"
            ;;
        Linux)
            hostname -I | awk '{print $1}'
            ;;
        *)
            echo "192.168.1.100"
            ;;
    esac
}

LOCAL_IP=$(get_local_ip)

echo ""
echo "検出されたIPアドレス: $LOCAL_IP"
echo ""

# 証明書を生成
echo "証明書を生成中..."
cd "$CERTS_DIR"
mkcert -key-file key.pem -cert-file cert.pem localhost 127.0.0.1 "$LOCAL_IP"

echo ""
echo "=== セットアップ完了 ==="
echo ""
echo "証明書が $CERTS_DIR に生成されました:"
echo "  - cert.pem (証明書)"
echo "  - key.pem (秘密鍵)"
echo ""
echo "【重要】iPad/スマホでカメラを使用するには、以下の手順が必要です:"
echo ""
echo "1. CA証明書をモバイルデバイスにインストール:"
echo "   CA証明書の場所: $(mkcert -CAROOT)/rootCA.pem"
echo ""
echo "2. iOSの場合:"
echo "   - 上記ファイルをAirDropまたはメールでiPad/iPhoneに送信"
echo "   - 設定 > 一般 > VPNとデバイス管理 > プロファイルをインストール"
echo "   - 設定 > 一般 > 情報 > 証明書信頼設定 > ルート証明書を有効化"
echo ""
echo "3. Androidの場合:"
echo "   - 上記ファイルをデバイスに転送"
echo "   - 設定 > セキュリティ > 暗号化と認証情報 > 証明書をインストール"
echo ""
echo "アクセスURL: https://$LOCAL_IP:3002"
echo ""
