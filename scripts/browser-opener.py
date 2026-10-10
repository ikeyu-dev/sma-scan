#!/usr/bin/env python3
"""SSEで受け取ったURLをホストPCのブラウザで開く。"""

import json
import os
import sys
import time
import webbrowser

import requests


def main():
    api_url = sys.argv[1] if len(sys.argv) > 1 else "https://localhost:8002"
    headers = {"X-Scan-Token": os.environ["SCAN_TOKEN"]}
    certificate = os.environ.get("SCAN_CERT", "certs/cert.pem")

    print(f"SSEストリームに接続中: {api_url}/stream")
    try:
        while True:
            try:
                with requests.get(
                    f"{api_url}/stream",
                    headers=headers,
                    stream=True,
                    verify=certificate,
                    timeout=(5, 15),
                ) as response:
                    response.raise_for_status()
                    for line in response.iter_lines(chunk_size=1, decode_unicode=True):
                        if not line or not line.startswith("data: "):
                            continue
                        event = json.loads(line[6:])
                        print(f"URL受信: {event['url']}")
                        try:
                            success = webbrowser.open(event["url"])
                        except Exception as exc:
                            print(f"ブラウザ起動エラー: {exc}")
                            success = False
                        result = requests.post(
                            f"{api_url}/opened/{event['id']}",
                            headers=headers,
                            json={"success": success},
                            verify=certificate,
                            timeout=5,
                        )
                        result.raise_for_status()
            except requests.RequestException as exc:
                print(f"接続エラー: {exc}。3秒後に再接続します")
                time.sleep(3)
    except KeyboardInterrupt:
        print("\n終了します")


if __name__ == "__main__":
    main()
