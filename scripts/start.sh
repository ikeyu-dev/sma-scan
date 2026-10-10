#!/bin/bash

# スマスキャン - Docker起動スクリプト

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CERTS_DIR="$PROJECT_DIR/certs"

echo "=== スマスキャン Docker起動 ==="
echo ""

# 証明書の存在確認
if [ ! -f "$CERTS_DIR/cert.pem" ] || [ ! -f "$CERTS_DIR/key.pem" ]; then
    echo "エラー: 証明書が見つかりません"
    echo "先に ./scripts/setup-certs.sh を実行してください"
    exit 1
fi

# IPアドレスを取得
get_local_ip() {
    case "$(uname -s)" in
        Darwin)
            ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost"
            ;;
        Linux)
            hostname -I | awk '{print $1}'
            ;;
        *)
            echo "localhost"
            ;;
    esac
}

LOCAL_IP=$(get_local_ip)
export HOST_IP=$LOCAL_IP
export SCAN_TOKEN="$(openssl rand -hex 16)"
export SCAN_CERT="$(mkcert -CAROOT)/rootCA.pem"

echo "検出されたIPアドレス: $LOCAL_IP"
echo ""
echo "フロントエンド: https://$LOCAL_IP:3002"
echo "バックエンド:   https://$LOCAL_IP:8002"
echo ""
echo "iPad/スマホからは以下のURLにアクセスしてください:"
echo "https://$LOCAL_IP:3002/#token=$SCAN_TOKEN"
echo "接続コード: $SCAN_TOKEN"
echo ""

# Dockerコンテナを起動
cd "$PROJECT_DIR"
docker compose up --build -d

echo ""
echo "コンテナが起動しました"
echo ""
echo "ブラウザオープナーを起動中..."
echo "（QRコードを読み取るとブラウザでURLが開きます）"
echo ""
echo "終了するには Ctrl+C を押してください"
echo ""

# ブラウザオープナーを起動
trap 'docker compose down' EXIT
pip install -q requests 2>/dev/null || true
python3 "$SCRIPT_DIR/browser-opener.py" "https://$LOCAL_IP:8002"

# 終了時にコンテナを停止
echo ""
echo "コンテナを停止中..."
