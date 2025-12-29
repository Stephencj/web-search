#!/usr/bin/env python3
import asyncio
import httpx

async def fetch():
    from app.services.redbar_auth_service import get_redbar_auth_service
    from app.database import get_session_factory

    async with get_session_factory()() as db:
        auth = get_redbar_auth_service()
        cookies = await auth.get_session_cookies(db)
        print(f"Authenticated: {bool(cookies)}")

        async with httpx.AsyncClient(timeout=30) as c:
            url = "https://redbarradio.net/embed/vod2?id=REDBAR-S22-E05"
            r = await c.get(url, cookies=cookies)
            print(f"Status: {r.status_code}")
            print(f"Length: {len(r.text)}")

            # Save to file
            with open('/tmp/embed_auth.html', 'w') as f:
                f.write(r.text)
            print("Saved to /tmp/embed_auth.html")

            # Print key parts
            import re
            vid_urls = re.findall(r'vid\.redbarradio\.com[^\s"\'<>]*', r.text)
            m3u8_urls = re.findall(r'https?://[^\s"\'<>]*\.m3u8[^\s"\'<>]*', r.text)
            src_tags = re.findall(r'<source[^>]+>', r.text)

            print(f"\nvid URLs: {vid_urls}")
            print(f"m3u8 URLs: {m3u8_urls}")
            print(f"source tags: {src_tags}")

if __name__ == "__main__":
    asyncio.run(fetch())
