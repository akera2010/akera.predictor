"""Telegram alerts for strong value bets (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID)."""
from __future__ import annotations

import logging

import httpx

from ..config import APP_NAME, env

log = logging.getLogger("akeraten.telegram")
_sent: set[str] = set()


def enabled() -> bool:
    return bool(env("TELEGRAM_BOT_TOKEN") and env("TELEGRAM_CHAT_ID"))


def format_bet(b: dict) -> str:
    flag = " ⚠️ SOSPECHOSO" if b.get("suspicious") else ""
    return (f"🎾 {APP_NAME} – value bet{flag}\n"
            f"{b['player_a']} vs {b['player_b']} ({b.get('tournament') or ''})\n"
            f"Selección: {b['selection']} @ {b['odds']} ({b.get('bookmaker') or 'n/d'})\n"
            f"Prob. modelo {b['model_prob']:.1%} | implícita {b['implied_prob']:.1%} | edge {b['edge']:.1%}\n"
            f"Stake sugerido: {b['stake']} (Kelly x{b['kelly_fraction']:.2f}) | confianza {b['confidence']}\n"
            f"{'[DEMO] ' if b.get('source') == 'demo' else ''}No es garantía de beneficio. Juega con responsabilidad.")


def send_alert(bet: dict) -> bool:
    if not enabled() or bet["id"] in _sent:
        return False
    _sent.add(bet["id"])
    try:
        r = httpx.post(f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}/sendMessage",
                       json={"chat_id": env("TELEGRAM_CHAT_ID"), "text": format_bet(bet)}, timeout=10)
        return r.status_code == 200
    except httpx.HTTPError as e:
        log.warning("telegram send failed: %s", e)
        return False
