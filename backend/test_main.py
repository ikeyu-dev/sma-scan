"""QRの受付からPC側の結果通知までを確認する。"""

import asyncio
import json
import os
import unittest

import httpx

os.environ["SCAN_TOKEN"] = "test-token"

import main  # noqa: E402


class ScanApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=main.app),
            base_url="http://testserver",
        )
        main.opener_connected = False
        main.pending_results.clear()
        main.scan_history.clear()
        main.pending_urls = asyncio.Queue()

    async def asyncTearDown(self):
        await self.client.aclose()
        main.opener_connected = False

    async def test_requires_connection_code(self):
        response = await self.client.post("/scan", json={"url": "https://example.com"})
        self.assertEqual(response.status_code, 401)

    async def test_rejects_non_web_urls(self):
        response = await self.client.post(
            "/scan",
            headers={"X-Scan-Token": "test-token"},
            json={"url": "file:///etc/passwd"},
        )
        self.assertEqual(response.status_code, 422)

    async def test_reports_disconnected_opener(self):
        response = await self.client.post(
            "/scan",
            headers={"X-Scan-Token": "test-token"},
            json={"url": "https://example.com"},
        )
        self.assertEqual(response.status_code, 503)

    async def test_waits_for_browser_result(self):
        main.opener_connected = True
        request = asyncio.create_task(
            self.client.post(
                "/scan",
                headers={"X-Scan-Token": "test-token"},
                json={"url": "https://example.com"},
            )
        )
        event_id, url = await asyncio.wait_for(main.pending_urls.get(), timeout=1)
        self.assertEqual(url, "https://example.com")
        self.assertFalse(request.done())
        acknowledged = await self.client.post(
            f"/opened/{event_id}",
            headers={"X-Scan-Token": "test-token"},
            json={"success": True},
        )
        self.assertEqual(acknowledged.status_code, 200)
        response = await request
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    async def test_reports_browser_failure(self):
        main.opener_connected = True
        request = asyncio.create_task(
            self.client.post(
                "/scan",
                headers={"X-Scan-Token": "test-token"},
                json={"url": "https://example.com"},
            )
        )
        event_id, _ = await asyncio.wait_for(main.pending_urls.get(), timeout=1)
        await self.client.post(
            f"/opened/{event_id}",
            headers={"X-Scan-Token": "test-token"},
            json={"success": False},
        )
        self.assertEqual((await request).status_code, 502)

    async def test_stream_delivers_one_json_event(self):
        response = await main.stream_urls()
        stream = response.body_iterator
        self.assertEqual(await anext(stream), ": connected\n\n")
        result = asyncio.get_running_loop().create_future()
        main.pending_results["event-1"] = result
        await main.pending_urls.put(("event-1", "https://example.com/a?b=1"))
        event = await asyncio.wait_for(anext(stream), timeout=1)
        self.assertEqual(
            json.loads(event.removeprefix("data: ").strip()),
            {"id": "event-1", "url": "https://example.com/a?b=1"},
        )
        await stream.aclose()
        self.assertFalse(main.opener_connected)


if __name__ == "__main__":
    unittest.main()
