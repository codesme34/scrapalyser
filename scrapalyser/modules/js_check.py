from bs4 import BeautifulSoup


# ids of the mount points used by SPA frameworks
JS_ROOT_IDS = ["root", "app", "__next", "__nuxt", "nuxt", "svelte"]

MIN_CONTENT_LENGTH = 500

NON_VISIBLE_TAGS = ["script", "style", "noscript", "template"]


async def detect(url: str, html: str) -> dict:
    try:
        soup = BeautifulSoup(html, "html.parser")

        # No scripts at all — static HTML, JS not required
        script_count = len(soup.find_all("script"))
        if script_count == 0:
            return {"js_required": False}

        # Only count text a user actually sees (inline JSON / CSS excluded)
        for tag in soup(NON_VISIBLE_TAGS):
            tag.decompose()
        body = soup.body or soup
        body_text = body.get_text(" ", strip=True)

        if len(body_text) < MIN_CONTENT_LENGTH:
            # SPA shell detection: root/app mount point + low text content
            if any(soup.find(id=root_id) is not None for root_id in JS_ROOT_IDS):
                return {"js_required": True}

            # Very low text content with many scripts — likely a SPA
            if script_count > 3:
                return {"js_required": True}

        return {"js_required": False}
    except Exception:
        return None
