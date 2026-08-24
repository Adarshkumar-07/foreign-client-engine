import re
import httpx
from bs4 import BeautifulSoup


async def check_website(url: str | None):
    if not url or not url.strip():
        return {
            "exists": False,
            "status": "NO_WEBSITE",
            "https": False,
            "title": None,
            "meta_description": None,
            "has_viewport": False,
            "has_form": False,
            "has_phone": False,
            "has_email": False,
            "has_cta": False,
            "problems": ["No website detected"]
        }

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        async with httpx.AsyncClient(
            timeout=10,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"}
        ) as client:

            response = await client.get(url)

        soup = BeautifulSoup(response.text, "html.parser")

        title = soup.title.string.strip() if soup.title and soup.title.string else None

        meta_tag = soup.find(
            "meta",
            attrs={"name": re.compile("^description$", re.I)}
        )

        meta_description = (
            meta_tag.get("content")
            if meta_tag else None
        )

        has_viewport = bool(
            soup.find(
                "meta",
                attrs={"name": re.compile("^viewport$", re.I)}
            )
        )

        has_form = bool(soup.find("form"))

        text = soup.get_text(" ", strip=True)

        has_phone = bool(
            re.search(
                r"\+?\d[\d\s().-]{7,}\d",
                text
            )
        )

        has_email = bool(
            re.search(
                r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
                text
            )
        )

        cta_words = [
            "contact us",
            "get started",
            "book now",
            "book appointment",
            "request a quote",
            "get a quote",
            "call now",
            "schedule"
        ]

        page_text = text.lower()

        has_cta = any(
            word in page_text
            for word in cta_words
        )

        problems = []

        if not url.startswith("https://"):
            problems.append("Website is not using HTTPS")

        if not title:
            problems.append("Missing page title")

        if not meta_description:
            problems.append("Missing meta description")

        if not has_viewport:
            problems.append("Missing mobile viewport tag")

        if not has_form:
            problems.append("No contact form detected")

        if not has_cta:
            problems.append("No clear call-to-action detected")

        return {
            "exists": True,
            "status": "ACTIVE",
            "http_status": response.status_code,
            "https": response.url.scheme == "https",
            "title": title,
            "meta_description": meta_description,
            "has_viewport": has_viewport,
            "has_form": has_form,
            "has_phone": has_phone,
            "has_email": has_email,
            "has_cta": has_cta,
            "problems": problems
        }

    except Exception as e:
        return {
            "exists": False,
            "status": "UNREACHABLE",
            "error": str(e),
            "problems": [
                "Website could not be reached"
            ]
        }