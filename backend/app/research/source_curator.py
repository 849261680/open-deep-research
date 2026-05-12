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

_TARGET_KEYWORDS = {
    "统计数据": frozenset({
        "data", "statistics", "statistical", "survey", "dataset", "census",
        "adoption rate", "sample size", "market size", "数据", "统计", "调研",
        "样本", "采用率", "市场规模",
    }),
    "行业报告": frozenset({
        "report", "whitepaper", "market", "industry", "research", "survey",
        "报告", "白皮书", "行业", "市场", "调研", "研究",
    }),
    "案例研究": frozenset({
        "case", "case study", "customer", "story", "use case", "案例", "客户",
        "实践", "落地", "应用",
    }),
    "论文": frozenset({
        "paper", "journal", "doi", "arxiv", "study", "conference", "论文",
        "期刊", "研究", "会议",
    }),
    "官方文档": frozenset({
        "official", "docs", "documentation", "developer", "manual", "guide",
        "官方", "文档", "指南", "手册",
    }),
}


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
        self,
        sources: list[ResearchSource],
        max_sources: int = 15,
        evidence_targets: list[str] | None = None,
    ) -> list[ResearchSource]:
        # 1. 计算评分
        targets = _normalize_targets(evidence_targets)
        scored = [
            (
                source,
                _score_source(source) + _target_bonus(source, targets),
                _matches_targets(source, targets),
            )
            for source in sources
        ]

        # 2. 去重
        seen_links: set[str] = set()
        unique: list[tuple[ResearchSource, float, bool]] = []
        for source, score, matches_targets in scored:
            if not source.link or source.link in seen_links:
                continue
            seen_links.add(source.link)
            # 过滤掉完全无内容且评分极低的来源
            if not (source.extracted_content or source.snippet) and score < 0.3:
                continue
            unique.append((source, score, matches_targets))

        matched = [item for item in unique if item[2]]
        if targets and matched:
            unique = [*matched, *[item for item in unique if not item[2] and item[1] >= 0.75]]

        # 3. 按可信度排序（高 → 低）
        unique.sort(key=lambda pair: pair[1], reverse=True)

        # 4. 取 top-N
        return [source for source, _score, _matches_targets in unique[:max_sources]]


def _normalize_targets(evidence_targets: list[str] | None) -> list[str]:
    """Keep known evidence target labels while preserving order."""
    normalized = []
    seen: set[str] = set()
    for target in evidence_targets or []:
        cleaned = target.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized


def _target_bonus(source: ResearchSource, targets: list[str]) -> float:
    """Give a source a quality boost when it matches evidence targets."""
    if not targets:
        return 0.0
    return 0.2 if _matches_targets(source, targets) else -0.15


def _matches_targets(source: ResearchSource, targets: list[str]) -> bool:
    """Check whether source text or URL matches one requested evidence target."""
    if not targets:
        return False
    haystack = " ".join(
        [
            source.title,
            source.link,
            source.snippet,
            source.extracted_content[:500],
        ]
    ).lower()
    for target in targets:
        keywords = _TARGET_KEYWORDS.get(target, frozenset({target.lower()}))
        if any(keyword.lower() in haystack for keyword in keywords):
            return True
    return False
