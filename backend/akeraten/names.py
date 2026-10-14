"""Player-name normalisation so 'Sinner J.', 'SINNER, Jannik' and 'Jannik Sinner'
resolve to the same player across providers."""
from __future__ import annotations

import re
import unicodedata


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm(s: str) -> str:
    s = strip_accents(s or "").lower()
    s = re.sub(r"[^a-z0-9一-鿿 ,.\-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def canonical(name: str) -> str:
    """'Sinner, Jannik' -> 'jannik sinner'."""
    n = norm(name)
    if "," in n:
        last, first = [x.strip() for x in n.split(",", 1)]
        n = f"{first} {last}"
    return re.sub(r"[.\-]", " ", n).replace("  ", " ").strip()


def keys(name: str) -> list[str]:
    """Lookup keys: full canonical name + 'surname initial' variants (both orders)."""
    c = canonical(name)
    parts = c.split()
    out = [c, c.replace(" ", "")]
    if len(parts) >= 2:
        first, last = parts[0], " ".join(parts[1:])
        out.append(f"{last} {first[0]}")
        # 'Sinner J' style (surname first, initial last)
        last2, first2 = " ".join(parts[:-1]), parts[-1]
        if len(first2) == 1:
            out.append(f"{last2} {first2}")
        out.append(f"{parts[-1]} {parts[0][0]}")
        out.append(f"{parts[0]} {parts[-1][0]}")  # surname-first convention ('Wang C.')
        # Asian order 'Wang Chuqin' vs 'Chuqin Wang'
        out.append(" ".join(reversed(parts)))
    return list(dict.fromkeys(out))


class NameIndex:
    def __init__(self, names=()):
        self._idx: dict[str, str] = {}
        for n in names:
            self.add(n)

    def add(self, name: str) -> None:
        for k in keys(name):
            self._idx.setdefault(k, name)

    def find(self, name: str) -> str | None:
        if not name:
            return None
        for k in keys(name):
            if k in self._idx:
                return self._idx[k]
        return None


def same_player(a: str, b: str) -> bool:
    ka, kb = set(keys(a)), set(keys(b))
    return bool(ka & kb)
