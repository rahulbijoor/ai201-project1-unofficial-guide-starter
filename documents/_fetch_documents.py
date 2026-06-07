"""
One-off collector for The Unofficial Guide (Milestone 1).

Domain: "Surviving grad school & academic life" -- the unofficial, student-to-student
advice that doesn't show up in any official handbook (dealing with advisors, imposter
syndrome, choosing courses, exam/publishing strategy, work-life survival).

Source: Academia Stack Exchange (https://academia.stackexchange.com), pulled via the
public Stack Exchange API. Each saved document is one Q&A thread: the question plus its
top-voted answers. This mirrors real forum/review-style student-generated knowledge.

Run once:  python documents/_fetch_documents.py
"""
import html
import json
import re
import time
import urllib.request
from pathlib import Path

API = "https://api.stackexchange.com/2.3"
SITE = "academia"
OUT = Path(__file__).parent
HEADERS = {"User-Agent": "ai201-unofficial-guide/1.0 (educational project)"}

# Hand-picked tags spanning a range of questions, so the docs aren't all near-duplicates.
TAGS = [
    "advisor", "graduate-school", "phd", "thesis",
    "coursework", "exams", "writing", "career-path",
]


def get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def clean(text):
    """Strip HTML tags -> readable plain text (light preprocessing)."""
    text = html.unescape(text or "")
    text = re.sub(r"<pre><code>(.*?)</code></pre>", r"\n\1\n", text, flags=re.S)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def slug(s, n=50):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:n].strip("-")


def fetch_thread(qid):
    q = get(f"{API}/questions/{qid}?site={SITE}&filter=withbody")["items"][0]
    ans = get(
        f"{API}/questions/{qid}/answers?site={SITE}&order=desc&sort=votes"
        f"&pagesize=4&filter=withbody"
    )["items"]
    return q, ans


def main():
    seen, saved = set(), 0
    for tag in TAGS:
        if saved >= 14:
            break
        url = (
            f"{API}/questions?order=desc&sort=votes&site={SITE}"
            f"&tagged={tag}&pagesize=2&filter=withbody"
        )
        for q in get(url)["items"]:
            qid = q["question_id"]
            if qid in seen:
                continue
            seen.add(qid)
            try:
                question, answers = fetch_thread(qid)
            except Exception as e:
                print("  skip", qid, e)
                continue
            title = html.unescape(question["title"])
            lines = [
                f"# {title}",
                "",
                f"Source: Academia Stack Exchange",
                f"URL: {question['link']}",
                f"Tags: {', '.join(question['tags'])}",
                f"Question score: {question['score']} | Views: {question.get('view_count','?')}",
                "",
                "## Question",
                "",
                clean(question["body"]),
                "",
            ]
            for i, a in enumerate(answers, 1):
                badge = " (accepted)" if a.get("is_accepted") else ""
                lines += [
                    f"## Answer {i} (score {a['score']}){badge}",
                    "",
                    clean(a["body"]),
                    "",
                ]
            fname = OUT / f"{slug(title)}.md"
            fname.write_text("\n".join(lines), encoding="utf-8")
            saved += 1
            print(f"  saved [{saved}] {fname.name}")
            time.sleep(0.4)
    print(f"\nDone. {saved} documents written to {OUT}")


if __name__ == "__main__":
    main()
