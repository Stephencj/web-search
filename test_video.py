#!/usr/bin/env python3
import asyncio
import re
import httpx

async def fetch_and_analyze():
    from app.services.redbar_auth_service import get_redbar_auth_service
    from app.database import get_session_factory

    async with get_session_factory()() as db:
        auth = get_redbar_auth_service()
        cookies = await auth.get_session_cookies(db)
        print(f"Authenticated: {bool(cookies)}")

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            url = "https://redbarradio.net/shows/redbar-s22-e05"
            resp = await client.get(url, cookies=cookies)
            html = resp.text
            print(f"Page length: {len(html)}")

            # Find ALL video-related content
            patterns = [
                (r'vid\.redbarradio[^\s"\'<>]*', 'vid.redbarradio'),
                (r'https?://[^\s"\'<>]*\.m3u8[^\s"\'<>]*', 'm3u8 URLs'),
                (r'<video[^>]*>.*?</video>', 'video tags'),
                (r'<iframe[^>]*src="([^"]*)"', 'iframes'),
                (r'hls["\'\s:=]+["\'"]?([^"\'"\s>]+)', 'hls refs'),
                (r'jwplayer|videojs|plyr', 'players'),
                (r'encoded/[^\s"\'/<>]+', 'encoded paths'),
            ]

            for pattern, name in patterns:
                matches = re.findall(pattern, html, re.I | re.S)
                if matches:
                    print(f"\n{name}:")
                    for m in matches[:5]:
                        print(f"  {m[:200] if isinstance(m, str) else m}")

            # Save full HTML for inspection
            with open('/tmp/redbar_s22e05.html', 'w') as f:
                f.write(html)
            print("\nSaved full HTML to /tmp/redbar_s22e05.html")

if __name__ == "__main__":
    asyncio.run(fetch_and_analyze())
