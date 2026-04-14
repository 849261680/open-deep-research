from __future__ import annotations

from urllib.parse import urlparse

from .models import ResearchSource

# ── 来源可信度评估 ──────────────────────────────────────────────

# 高可信度域名后缀和关键词
_HIGH_CREDIBILITY_TLDS = frozenset({".gov", ".edu", ".mil", ".org"})
_HIGH_CREDIBILITY_KEYWORDS = frozenset({
    "wikipedia.org", "nature.com", "science.org", "arxiv.org",
    "ieee.org", "acm.org", "springer.com", "wiley.com",
    "reuters.com", "bloomberg.com", "apnews.com", "bbc.com",
    "nytimes.com", "wsj.com", "economist.com", "ft.com",
    "gov.cn", "statista.com", "who.int", "worldbank.org",
    "oecd.org", "un.org", "nih.gov", "mit.edu",
})

# 低可信度域名关键词
_LOW_CREDIBILITY_KEYWORDS = frozenset({
    "reddit.com", "twitter.com", "x.com", "facebook.com",
    "tiktok.com", "instagram.com", "weibo.com", "zhihu.com",
    "quora.com", "medium.com", "substack.com", "blogger.com",
    "wordpress.com", "tumblr.com", "pinterest.com",
    "youtube.com", "bilibili.com", "douyin.com",
})

# 垃圾/广告域名关键词
_SPAM_KEYWORDS = frozenset({
    "clickbait", "ad.", "ads.", "spam", "affiliate",
    "promo", "bonus", "free-download", "torrent",
})


def _score_source(source: ResearchSource) -> float:
    """为来源计算可信度评分（0.0 - 1.0）。"""
    if not source.link:
        return 0.0

    score = 0.5  # 基准分

    try:
        parsed = urlparse(source.link)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
    except Exception:  # noqa: BLE001
        return 0.3

    # 域名后缀加分
    for tld in _HIGH_CREDIBILITY_TLDS:
        if domain.endswith(tld):
            score += 0.25
            break

    # 权威媒体/学术加分
    for keyword in _HIGH_CREDIBILITY_KEYWORDS:
        if keyword in domain:
            score += 0.2
            break

    # 社交/UGC 降分
    for keyword in _LOW_CREDIBILITY_KEYWORDS:
        if keyword in domain:
            score -= 0.2
            break

    # 垃圾域名严重降分
    for keyword in _SPAM_KEYWORDS:
        if keyword in domain or keyword in path:
            score -= 0.5
            break

    # 有提取内容的加分
    if source.extracted_content and len(source.extracted_content) > 200:
        score += 0.1

    # 有 snippet 的略微加分
    if source.snippet and len(source.snippet) > 50:
        score += 0.05

    return max(0.0, min(1.0, score))


class SourceCurator:
    """Curates sources by deduping, scoring credibility, and keeping quality sources."""

    def curate(
        self, sources: list[ResearchSource], max_sources: int = 15
    ) -> list[ResearchSource]:
        # 1. 计算评分
        scored = [(source, _score_source(source)) for source in sources]

        # 2. 去重
        seen_links: set[str] = set()
        unique: list[tuple[ResearchSource, float]] = []
        for source, score in scored:
            if not source.link or source.link in seen_links:
                continue
            seen_links.add(source.link)
            # 过滤掉完全无内容且评分极低的来源
            if not (source.extracted_content or source.snippet) and score < 0.3:
                continue
            unique.append((source, score))

        # 3. 按可信度排序（高 → 低）
        unique.sort(key=lambda pair: pair[1], reverse=True)

        # 4. 取 top-N
        return [source for source, _score in unique[:max_sources]]
