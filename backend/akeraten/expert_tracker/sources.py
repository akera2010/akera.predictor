"""Fetchers for expert posts. Every fetcher is polite (rate-limited, cached,
identifies itself) and returns a list of {"id", "text", "timestamp", "url"}.
Without the required credential a fetcher returns [] and reports 'disabled'.

- twitter : X API v2 (TWITTER_BEARER_TOKEN) /2/users/by/username + /2/users/:id/tweets
- weibo   : public mobile container API (needs the expert's numeric uid in experts.json)
- instagram: Instagram Graph API (INSTAGRAM_ACCESS_TOKEN + INSTAGRAM_BUSINESS_ID, business discovery)
- website : plain GET + tag stripping (respect the site's robots.txt / ToS before enabling)
- api     : vendor APIs (e.g. STATSCORE TipsterAPI) - key named in experts.json "env"
- discord : webhook-IN: posts arrive via POST /api/experts/webhook/discord (no polling)
"""
from __future__ import annotations

import html
import re
from collections import deque

from ..config import env, env_bool
from ..data_ingestion.base import BaseClient

DISCORD_INBOX: deque = deque(maxlen=500)


class _Http(BaseClient):
    name = "expert_http"
    rate_limit_per_min = 12
    cache_ttl = 300

    @property
    def enabled(self) -> bool:
        return True


_http = None


def http() -> _Http:
    global _http
    if _http is None:
        _http = _Http()
    return _http


def fetch_twitter(expert: dict) -> list[dict]:
    token = env("TWITTER_BEARER_TOKEN")
    if not token or not expert.get("handle"):
        return []
    h = {"Authorization": f"Bearer {token}"}
    u = http().request("GET", f"https://api.twitter.com/2/users/by/username/{expert['handle']}", headers=h,
                       cache_ttl=86400)
    uid = (u.get("data") or {}).get("id") if isinstance(u, dict) else None
    if not uid:
        return []
    body = http().request("GET", f"https://api.twitter.com/2/users/{uid}/tweets", headers=h,
                          params={"max_results": 10, "tweet.fields": "created_at,lang"})
    return [{"id": t["id"], "text": t.get("text", ""), "timestamp": t.get("created_at"),
             "url": f"https://x.com/{expert['handle']}/status/{t['id']}"}
            for t in (body.get("data") or [] if isinstance(body, dict) else [])]


def fetch_weibo(expert: dict) -> list[dict]:
    uid = expert.get("uid")
    if not uid or not env_bool("ENABLE_WEIBO_SCRAPING"):
        return []
    body = http().request("GET", "https://m.weibo.cn/api/container/getIndex",
                          params={"containerid": f"107603{uid}"})
    cards = ((body or {}).get("data") or {}).get("cards") or [] if isinstance(body, dict) else []
    out = []
    for c in cards:
        mb = c.get("mblog")
        if mb:
            out.append({"id": mb.get("id"), "text": _strip(mb.get("text", "")), "timestamp": mb.get("created_at"),
                        "url": f"https://m.weibo.cn/detail/{mb.get('id')}"})
    return out


def fetch_instagram(expert: dict) -> list[dict]:
    token, biz = env("INSTAGRAM_ACCESS_TOKEN"), env("INSTAGRAM_BUSINESS_ID")
    if not token or not biz or not expert.get("handle"):
        return []
    fields = f"business_discovery.username({expert['handle']}){{media.limit(10){{id,caption,timestamp,permalink}}}}"
    body = http().request("GET", f"https://graph.facebook.com/v19.0/{biz}",
                          params={"fields": fields, "access_token": token})
    media = (((body or {}).get("business_discovery") or {}).get("media") or {}).get("data") or [] \
        if isinstance(body, dict) else []
    return [{"id": m["id"], "text": m.get("caption") or "", "timestamp": m.get("timestamp"), "url": m.get("permalink")}
            for m in media]


def fetch_website(expert: dict) -> list[dict]:
    if not env_bool("ENABLE_WEB_SCRAPING") or not str(expert.get("url", "")).startswith("http"):
        return []
    body = http().request("GET", expert["url"], cache_ttl=900)
    text = _strip(body if isinstance(body, str) else str(body))
    # split into paragraph-like chunks so the NLP sees one pick per chunk
    chunks = [c.strip() for c in re.split(r"(?:\n|\.\s)", text) if 20 < len(c.strip()) < 400]
    return [{"id": f"{expert['name']}-{abs(hash(c))}", "text": c, "timestamp": None, "url": expert["url"]}
            for c in chunks[:200]]


def fetch_api(expert: dict) -> list[dict]:
    key = env(expert.get("env", "")) if expert.get("env") else None
    if not key:
        return []
    base = env("STATSCORE_TIPSTER_URL")  # vendor endpoint is account specific
    if not base:
        return []
    body = http().request("GET", base, headers={"Authorization": f"Bearer {key}"})
    items = body.get("data", []) if isinstance(body, dict) else body if isinstance(body, list) else []
    return [{"id": str(i.get("id")), "text": i.get("text") or i.get("description") or "", "timestamp": i.get("created_at"),
             "url": base} for i in items if isinstance(i, dict)]


def fetch_discord(expert: dict) -> list[dict]:
    out = [m for m in list(DISCORD_INBOX) if m.get("expert", expert["name"]) == expert["name"]]
    return out


FETCHERS = {"twitter": fetch_twitter, "weibo": fetch_weibo, "instagram": fetch_instagram,
            "website": fetch_website, "api": fetch_api, "discord": fetch_discord}


def platform_enabled(expert: dict) -> bool:
    p = expert.get("platform")
    if p == "twitter":
        return bool(env("TWITTER_BEARER_TOKEN"))
    if p == "weibo":
        return bool(expert.get("uid")) and env_bool("ENABLE_WEIBO_SCRAPING")
    if p == "instagram":
        return bool(env("INSTAGRAM_ACCESS_TOKEN") and env("INSTAGRAM_BUSINESS_ID"))
    if p == "website":
        return env_bool("ENABLE_WEB_SCRAPING")
    if p == "api":
        return bool(expert.get("env") and env(expert["env"]) and env("STATSCORE_TIPSTER_URL"))
    if p == "discord":
        return True
    return False


def _strip(s: str) -> str:
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()
