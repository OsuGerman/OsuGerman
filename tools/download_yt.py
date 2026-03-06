import asyncio
import sys
import re
import subprocess

async def download_with_playwright(url: str, output_path: str):
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[
            '--no-sandbox',
            '--disable-dev-shm-usage',
        ])
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        print(f"Navigating to {url}...")
        await page.goto(url, wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)

        title = await page.title()
        print(f"Page title: {title}")

        audio_urls = []
        page.on('response', lambda resp: _collect_audio(resp, audio_urls))

        try:
            consent = page.locator('button:has-text("Accept")')
            if await consent.count() > 0:
                await consent.first.click()
                await asyncio.sleep(1)
        except Exception:
            pass

        try:
            dismiss = page.locator('button[aria-label="No thanks"]')
            if await dismiss.count() > 0:
                await dismiss.first.click()
                await asyncio.sleep(1)
        except Exception:
            pass

        try:
            play_btn = page.locator('button.ytp-large-play-button')
            if await play_btn.count() > 0:
                await play_btn.click()
                await asyncio.sleep(3)
        except Exception:
            pass

        page_html = await page.content()
        ytInitialPlayerResponse = re.search(
            r'ytInitialPlayerResponse\s*=\s*(\{.+?\});', page_html
        )

        if ytInitialPlayerResponse:
            import json
            try:
                data = json.loads(ytInitialPlayerResponse.group(1))
                streaming = data.get('streamingData', {})
                formats = streaming.get('adaptiveFormats', []) + streaming.get('formats', [])
                audio_fmts = [f for f in formats if f.get('mimeType', '').startswith('audio/')]
                if audio_fmts:
                    best = max(audio_fmts, key=lambda f: f.get('bitrate', 0))
                    audio_url = best.get('url')
                    if audio_url:
                        print(f"Found audio stream: bitrate={best.get('bitrate')}, mime={best.get('mimeType')}")
                        print(f"Downloading audio...")
                        subprocess.run([
                            'ffmpeg', '-y', '-i', audio_url,
                            '-vn', '-acodec', 'libmp3lame', '-q:a', '2',
                            output_path
                        ], capture_output=True)
                        print(f"Saved to {output_path}")
                        await browser.close()
                        return True
                    else:
                        sig_cipher = best.get('signatureCipher', '')
                        print(f"Audio needs cipher: {sig_cipher[:100]}...")
            except json.JSONDecodeError:
                pass

        await browser.close()
        return False


def _collect_audio(resp, urls):
    ct = resp.headers.get('content-type', '')
    if 'audio' in ct:
        urls.append(resp.url)


if __name__ == '__main__':
    url = sys.argv[1] if len(sys.argv) > 1 else 'https://www.youtube.com/watch?v=9a6KnXJtn5k'
    output = sys.argv[2] if len(sys.argv) > 2 else '/workspace/songs/back2me.mp3'
    result = asyncio.run(download_with_playwright(url, output))
    if not result:
        print("Playwright extraction failed, trying cookies approach...")
        sys.exit(1)
