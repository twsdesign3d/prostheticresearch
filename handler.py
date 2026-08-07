import re
import json
import httpx
from bs4 import BeautifulSoup
import runpod

DEFAULT_KEYWORDS = [
    "prosthetic socket",
    "adjustable socket",
    "vacuum suspension",
    "gel liners",
    "silicone liners",
    "randy alley",
    "martin bionics",
]

def google_patents_search_url(query: str):
    # Simple Google Patents search URL
    q = query.strip().replace(" ", "+")
    return f"https://patents.google.com/?q={q}&oq={q}"

def extract_patent_links(html: str, limit: int = 10):
    soup = BeautifulSoup(html, "lxml")
    links = []
    for a in soup.select("a[href^='/patent/']"):
        href = a.get("href", "")
        if href.startswith("/patent/") and href.count("/") == 2:
            url = "https://patents.google.com" + href
            if url not in links:
                links.append(url)
        if len(links) >= limit:
            break
    return links

def fetch_patent_page(client: httpx.Client, url: str):
    r = client.get(url, timeout=30)
    r.raise_for_status()
    return r.text

def parse_patent_basic(html: str, url: str):
    soup = BeautifulSoup(html, "lxml")

    # Title
    title = soup.select_one("meta[name='DC.title']")
    title = title.get("content") if title else None

    # Abstract
    abstract = soup.select_one("meta[name='DC.description']")
    abstract = abstract.get("content") if abstract else None

    # Publication / patent number (best-effort)
    pub = soup.select_one("meta[name='DC.identifier']")
    pub = pub.get("content") if pub else None

    # Assignee (best-effort)
    assignee = soup.select_one("meta[name='DC.contributor']")
    assignee = assignee.get("content") if assignee else None

    return {
        "url": url,
        "publication": pub,
        "title": title,
        "assignee": assignee,
        "abstract": abstract,
        "notes": "Parsed from Google Patents HTML (best-effort). Add legal status extraction later.",
    }

def make_blog_draft(query: str, items: list, tone: str):
    lines = []
    lines.append(f"# Expired/Abandoned Prosthetic Patents: Research Roundup")
    lines.append("")
    lines.append(f"**Query:** {query}")
    lines.append("")
    lines.append("## What this is")
    lines.append(
        "This article curates older prosthetic and liner-related patents to inspire modern, safer, more manufacturable designs. "
        "This is educational research only—not legal advice and not medical advice."
    )
    lines.append("")
    lines.append("## Patents reviewed")
    for i, p in enumerate(items, 1):
        lines.append(f"### {i}) {p.get('title') or 'Untitled'}")
        lines.append(f"- Link: {p.get('url')}")
        if p.get("assignee"):
            lines.append(f"- Assignee: {p.get('assignee')}")
        if p.get("publication"):
            lines.append(f"- Identifier: {p.get('publication')}")
        if p.get("abstract"):
            lines.append("")
            lines.append("**Summary (from abstract):**")
            lines.append(p["abstract"])
        lines.append("")
        lines.append("**Content angle / what to explore today:**")
        lines.append("- What problem it solves")
        lines.append("- What you could modernize (materials, sensors, manufacturing)")
        lines.append("- Safety considerations and clinical validation needs")
        lines.append("")

    lines.append("## Disclaimer")
    lines.append(
        "Patent status (expired/abandoned) must be verified with authoritative legal-status sources before relying on it. "
        "Nothing here is legal advice."
    )
    return "\n".join(lines)

def handler(event):
    inp = event.get("input", {}) or {}

    # Your defaults
    keywords = inp.get("keywords") or DEFAULT_KEYWORDS
    tone = inp.get("tone", "educated")
    limit = int(inp.get("limit", 10))

    # Build a single query string
    query = inp.get("query")
    if not query:
        query = " OR ".join([f"\"{k}\"" for k in keywords])

    search_url = google_patents_search_url(query)

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; RunpodPatentCurator/1.0; +https://runpod.io/)"
    }

    results = []
    with httpx.Client(headers=headers, follow_redirects=True) as client:
        search_html = client.get(search_url, timeout=30).text
        patent_links = extract_patent_links(search_html, limit=limit)

        for url in patent_links:
            try:
                html = fetch_patent_page(client, url)
                results.append(parse_patent_basic(html, url))
            except Exception as e:
                results.append({"url": url, "error": str(e)})

    blog = make_blog_draft(query=query, items=results, tone=tone)

    return {
        "query": query,
        "limit": limit,
        "search_url": search_url,
        "results": results,
        "blog_draft_markdown": blog,
    }

runpod.serverless.start({"handler": handler})
