"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Html5Qrcode } from "html5-qrcode";

interface QrScannerProps {
    apiEndpoint: string;
}

export default function QrScanner({ apiEndpoint }: QrScannerProps) {
    const [token, setToken] = useState("");
    const [tokenInput, setTokenInput] = useState("");
    const [isScanning, setIsScanning] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [lastScannedUrl, setLastScannedUrl] = useState<string | null>(null);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const scannerRef = useRef<Html5Qrcode | null>(null);
    const startPromiseRef = useRef<Promise<unknown> | null>(null);
    const scanInProgressRef = useRef(false);

    useEffect(() => {
        const fromLink = new URLSearchParams(window.location.hash.slice(1)).get(
            "token"
        );
        const saved =
            fromLink || window.localStorage.getItem("scan-token") || "";
        if (saved) {
            window.localStorage.setItem("scan-token", saved);
            setToken(saved);
            setTokenInput(saved);
        }
        if (fromLink) {
            window.history.replaceState(null, "", window.location.pathname);
        }
    }, []);

    const stopScanner = useCallback(async () => {
        try {
            await startPromiseRef.current;
            if (scannerRef.current?.isScanning) {
                await scannerRef.current.stop();
            }
        } catch {
            // 起動失敗時は停止処理を続ける。
        } finally {
            scannerRef.current = null;
            startPromiseRef.current = null;
            setIsScanning(false);
        }
    }, []);

    const processQr = useCallback(
        async (url: string) => {
            if (scanInProgressRef.current) return;
            scanInProgressRef.current = true;
            setErrorMessage(null);
            setIsLoading(true);
            await stopScanner();

            try {
                const parsed = new URL(url);
                if (!["http:", "https:"].includes(parsed.protocol)) {
                    throw new Error("HTTPまたはHTTPSのURLを読み取ってください");
                }
                const response = await fetch(apiEndpoint, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-Scan-Token": token,
                    },
                    body: JSON.stringify({ url }),
                });
                const result = await response.json();
                if (!response.ok || !result.success) {
                    if (response.status === 401) {
                        window.localStorage.removeItem("scan-token");
                        setToken("");
                    }
                    const message =
                        typeof result.detail === "string"
                            ? result.detail
                            : response.status === 422
                              ? "HTTPまたはHTTPSのURLを読み取ってください"
                              : result.message || "送信に失敗しました";
                    throw new Error(message);
                }
                setLastScannedUrl(url);
            } catch (error) {
                setErrorMessage(
                    error instanceof Error
                        ? error.message
                        : "送信に失敗しました"
                );
            } finally {
                setIsLoading(false);
            }
        },
        [apiEndpoint, stopScanner, token]
    );

    const startScanner = useCallback(async () => {
        if (!token || scannerRef.current || startPromiseRef.current) return;
        scanInProgressRef.current = false;
        setLastScannedUrl(null);
        setErrorMessage(null);
        const scanner = new Html5Qrcode("qr-reader", { verbose: false });
        scannerRef.current = scanner;
        const starting = scanner.start(
            { facingMode: "environment" },
            { fps: 10, qrbox: { width: 250, height: 250 } },
            (decodedText) => void processQr(decodedText),
            () => {}
        );
        startPromiseRef.current = starting;
        try {
            await starting;
            setIsScanning(true);
        } catch (error) {
            scannerRef.current = null;
            setErrorMessage(
                error instanceof Error
                    ? error.message
                    : "カメラの起動に失敗しました"
            );
        } finally {
            startPromiseRef.current = null;
        }
    }, [processQr, token]);

    useEffect(() => {
        if (!token) return;
        const timer = window.setTimeout(() => void startScanner(), 100);
        return () => {
            window.clearTimeout(timer);
            void stopScanner();
        };
    }, [startScanner, stopScanner, token]);

    const saveToken = () => {
        const value = tokenInput.trim();
        if (!value) return;
        window.localStorage.setItem("scan-token", value);
        setToken(value);
    };

    return (
        <div className="flex w-full max-w-md flex-col items-center gap-4 p-4">
            <h1 className="text-2xl font-bold">スマスキャン</h1>

            {errorMessage && (
                <div
                    className="alert alert-error w-full"
                    role="alert"
                >
                    {errorMessage}
                </div>
            )}

            {!token ? (
                <div className="flex w-full flex-col gap-2">
                    <p>
                        PCの起動画面に表示された接続コードを入力してください。
                    </p>
                    <input
                        className="input input-bordered w-full"
                        aria-label="接続コード"
                        value={tokenInput}
                        onChange={(event) => setTokenInput(event.target.value)}
                    />
                    <button
                        className="btn btn-primary"
                        onClick={saveToken}
                    >
                        接続する
                    </button>
                </div>
            ) : (
                <>
                    {isLoading && <p>PCでブラウザを開いています...</p>}
                    <div
                        id="qr-reader"
                        className="aspect-square w-full overflow-hidden rounded-lg bg-base-200"
                    />
                    {lastScannedUrl && (
                        <div
                            className="alert alert-success w-full"
                            role="status"
                        >
                            <div>
                                <p>PCでブラウザを開きました</p>
                                <p className="break-all text-sm">
                                    {lastScannedUrl}
                                </p>
                            </div>
                        </div>
                    )}
                    <button
                        className={`btn w-full ${isScanning ? "btn-error" : "btn-primary"}`}
                        disabled={isLoading}
                        onClick={() =>
                            void (isScanning ? stopScanner() : startScanner())
                        }
                    >
                        {isScanning
                            ? "スキャンを停止"
                            : lastScannedUrl
                              ? "次のQRコードを読み取る"
                              : "スキャンを開始"}
                    </button>
                </>
            )}
            <style
                jsx
                global
            >{`
                #qr-reader video {
                    width: 100% !important;
                    height: 100% !important;
                    object-fit: cover !important;
                }
                #qr-reader__status_span,
                #qr-reader__dashboard_section_csr,
                #qr-reader__dashboard_section_fsr,
                #qr-reader__header_message {
                    display: none !important;
                }
            `}</style>
        </div>
    );
}
