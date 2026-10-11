"use client";

import dynamic from "next/dynamic";

const QrScanner = dynamic(() => import("@/components/QrScanner"), {
    ssr: false,
    loading: () => (
        <div className="flex items-center justify-center h-screen">
            <span className="loading loading-spinner loading-lg"></span>
        </div>
    ),
});

/**
 * Sma-Scan - メインページ
 * QRコードを読み取ってサーバーに送信する
 */
export default function Home() {
    const apiEndpoint =
        process.env.NEXT_PUBLIC_API_ENDPOINT || "https://localhost:8002/scan";

    return (
        <main className="min-h-screen flex items-center justify-center bg-base-100">
            <QrScanner apiEndpoint={apiEndpoint} />
        </main>
    );
}
