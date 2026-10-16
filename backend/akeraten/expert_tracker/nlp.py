"""Tiny rule-based NLP: turns an expert's post (Spanish / English / French /
Chinese) into (match, predicted_winner, confidence). Deliberately simple and
transparent; it errs on the side of NOT extracting a pick when unsure."""
from __future__ import annotations

import re

from ..names import canonical, strip_accents

ZH_NAMES = {
    "王楚钦": "Wang Chuqin", "樊振东": "Fan Zhendong", "林诗栋": "Lin Shidong", "梁靖崑": "Liang Jingkun",
    "向鹏": "Xiang Peng", "周启豪": "Zhou Qihao", "林高远": "Lin Gaoyuan", "孙颖莎": "Sun Yingsha",
    "王曼昱": "Wang Manyu", "陈幸同": "Chen Xingtong", "王艺迪": "Wang Yidi", "蒯曼": "Kuai Man",
    "张本智和": "Tomokazu Harimoto", "张本美和": "Miwa Harimoto", "莫雷加德": "Truls Moregard",
    "卡尔德拉诺": "Hugo Calderano", "林昀儒": "Lin Yun-Ju", "早田希娜": "Hina Hayata", "伊藤美诚": "Mima Ito",
    "郑钦文": "Zheng Qinwen", "辛纳": "Jannik Sinner", "阿尔卡拉斯": "Carlos Alcaraz", "德约科维奇": "Novak Djokovic",
    "萨巴伦卡": "Aryna Sabalenka", "斯瓦泰克": "Iga Swiatek",
}
WIN_WORDS = [
    # en
    "to win", "wins", "win", "beat", "beats", "over", "pick", "ml", "moneyline", "back", "take", "lock", "bet on",
    # es
    "gana", "ganara", "ganará", "victoria", "vence", "vencera", "se impone", "pronostico", "pronóstico", "apuesta",
    "favorito", "derrota a",
    # fr
    "gagne", "victoire", "bat", "pari", "prono",
    # zh
    "赢", "胜", "获胜", "晋级", "看好", "击败", "力挫", "拿下",
]
BEAT_WORDS = ["beat", "beats", "over", "def.", "defeats", "vence a", "derrota a", "bat", "击败", "力挫"]
HIGH = ["lock", "banker", "max bet", "maximum", "nailed", "seguro", "fijo", "clarisimo", "clarísimo", "bomba",
        "sûr", "sur ", "稳", "必胜", "强烈", "重注"]
LOW = ["maybe", "might", "could", "lean", "slight", "quizas", "quizás", "tal vez", "puede", "peut-être",
       "可能", "或许", "小注"]


def _norm(text: str) -> str:
    return strip_accents(text or "").lower()


def _name_tokens(name: str) -> list[str]:
    parts = canonical(name).split()
    toks = [canonical(name)]
    if len(parts) >= 2:
        toks += [parts[-1], parts[0]] if len(parts[-1]) > 3 else [parts[0]]
        if len(parts) >= 3:
            toks.append(" ".join(parts[1:]))
    return [t for t in toks if len(t) >= 3]


def _mentions(text_n: str, raw: str, name: str) -> list[tuple[int, int, str]]:
    """All (start, end, which_text) mentions of a player in the normalised or raw text."""
    out = []
    for zh, en in ZH_NAMES.items():
        if en == name:
            out += [(m.start(), m.end(), "raw") for m in re.finditer(re.escape(zh), raw)]
    for tok in _name_tokens(name):
        out += [(m.start(), m.end(), "n") for m in re.finditer(r"(?<![a-z])" + re.escape(tok) + r"(?![a-z])", text_n)]
    return out


def _find(text_n: str, raw: str, name: str) -> int | None:
    ms = _mentions(text_n, raw, name)
    return min(m[0] for m in ms) if ms else None


def _win_after(text_n: str, raw: str, name: str) -> int | None:
    """Distance (chars) from a mention of `name` to the next win keyword, if within 25 chars."""
    best = None
    for start, end, src in _mentions(text_n, raw, name):
        tail = (raw if src == "raw" else text_n)[end:end + 25]
        for w in WIN_WORDS:
            if w in BEAT_WORDS:
                continue
            m = re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", tail)
            if m and (best is None or m.start() < best):
                best = m.start()
    return best


def _confidence(text_n: str, raw: str) -> float:
    m = re.search(r"(\d{2})\s?%", text_n)
    if m:
        return min(0.95, max(0.5, int(m.group(1)) / 100))
    m = re.search(r"(?:stake|conf(?:idence|ianza)?|confianza)\s*[:=]?\s*(\d{1,2})\s*/\s*10", text_n)
    if m:
        return min(0.9, 0.5 + int(m.group(1)) * 0.04)
    c = 0.62
    if any(w in text_n or w in raw for w in HIGH):
        c += 0.13
    if any(w in text_n or w in raw for w in LOW):
        c -= 0.07
    return round(min(0.9, max(0.52, c)), 3)


def extract_picks(text: str, matches: list[dict]) -> list[dict]:
    """Return [{match_id, predicted_winner: name, side: 'a'|'b', confidence}] for
    every candidate match whose players are mentioned with a pick keyword."""
    raw = text or ""
    tn = _norm(raw)
    has_win = any(w in tn or w in raw for w in WIN_WORDS)
    out = []
    for m in matches:
        pa, pb = _find(tn, raw, m["player_a"]), _find(tn, raw, m["player_b"])
        if pa is None and pb is None:
            continue
        if not has_win and (pa is None or pb is None):
            continue
        if pa is not None and pb is not None:
            wa, wb = _win_after(tn, raw, m["player_a"]), _win_after(tn, raw, m["player_b"])
            first = "a" if pa < pb else "b"
            between = tn[min(pa, pb): max(pa, pb)] + raw[min(pa, pb): max(pa, pb)]
            if wa is not None or wb is not None:
                side = "a" if (wb is None or (wa is not None and wa <= wb)) else "b"
            elif any(w in between for w in BEAT_WORDS):
                side = first
            else:
                continue
        else:
            side = "a" if pa is not None else "b"
        out.append({"match_id": m.get("id") or m.get("match_id"), "side": side,
                    "predicted_winner": m["player_a"] if side == "a" else m["player_b"],
                    "confidence": _confidence(tn, raw)})
    return out
