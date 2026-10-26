"""
units.py — Indian financial units, normalised to ₹ crore.

Annual reports state the same quantity as "₹ 1,23,456 lakh", "₹ 1,234.56 crore",
"₹ 12,345.6 million", "INR 1.2 billion" or "$ 500 million" — sometimes in the
same report. LLMs mix these up constantly (a lakh is 10^5, a crore 10^7, a
million 10^6), so the answer layer normalises every figure it quotes, and the
eval set has questions designed to catch exactly this mistake.

    1 crore   = 100 lakh   = 10,000,000
    1 million = 10 lakh    = 0.1 crore
    1 billion = 100 crore

Indian digit grouping (12,34,567) is accepted alongside Western (1,234,567).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# multiplier to convert ONE unit into crore
TO_CRORE: dict[str, float] = {
    "crore": 1.0, "crores": 1.0, "cr": 1.0, "cr.": 1.0,
    "lakh": 0.01, "lakhs": 0.01, "lac": 0.01, "lacs": 0.01,
    "million": 0.1, "mn": 0.1, "mn.": 0.1, "m": 0.1,
    "billion": 100.0, "bn": 100.0, "bn.": 100.0, "b": 100.0,
    "thousand": 0.0001, "k": 0.0001,
    "": 1e-7,   # a bare rupee amount
}

_NUMBER = r"(?P<num>\d{1,3}(?:,\d{2,3})*(?:\.\d+)?|\d+(?:\.\d+)?)"
_UNIT = r"(?P<unit>crores?|cr\.?|lakhs?|lacs?|million|mn\.?|billion|bn\.?|thousand)?"
_CURRENCY = r"(?P<cur>₹|rs\.?|inr|\$|usd|us\$)?"

# "₹ 1,234.5 crore", "Rs. 12,34,567 lakh", "INR 500 million", "1,234 crore"
_AMOUNT = re.compile(
    rf"{_CURRENCY}\s*{_NUMBER}\s*{_UNIT}\b", re.IGNORECASE
)


@dataclass(frozen=True)
class Amount:
    value: float          # as written
    unit: str             # as written, lowercased, "" if none
    currency: str         # "INR", "USD" or ""
    crore: float | None   # normalised; None for non-INR

    def __str__(self) -> str:
        if self.crore is None:
            return f"{self.currency} {self.value:g} {self.unit}".strip()
        return f"₹ {self.crore:,.2f} crore"


def _currency(tok: str | None) -> str:
    if not tok:
        return ""
    t = tok.lower()
    if t in ("$", "usd", "us$"):
        return "USD"
    return "INR"


def to_crore(value: float, unit: str) -> float:
    """Convert a value in `unit` (lakh/crore/million/...) to crore."""
    key = unit.lower().rstrip(".") if unit else ""
    if key not in TO_CRORE and key + "." not in TO_CRORE:
        raise ValueError(f"unknown unit: {unit!r}")
    return value * TO_CRORE.get(key, TO_CRORE.get(key + ".", 1.0))


def parse_amount(text: str) -> Amount | None:
    """Parse the first money amount in `text`. Returns None if nothing looks like one."""
    m = _AMOUNT.search(text)
    if not m or not m.group("num"):
        return None
    value = float(m.group("num").replace(",", ""))
    unit = (m.group("unit") or "").lower().rstrip(".")
    cur = _currency(m.group("cur"))
    # A bare number with no unit and no currency is not an amount.
    if not unit and not cur:
        return None
    crore = to_crore(value, unit) if cur != "USD" else None
    return Amount(value=value, unit=unit, currency=cur, crore=crore)


def find_amounts(text: str) -> list[Amount]:
    """All money amounts in `text`, in order."""
    out = []
    for m in _AMOUNT.finditer(text):
        a = parse_amount(m.group(0))
        if a:
            out.append(a)
    return out


def format_crore(crore: float) -> str:
    """₹ 1,23,456.78 crore in Indian digit grouping."""
    whole, _, frac = f"{crore:.2f}".partition(".")
    neg = whole.startswith("-")
    whole = whole.lstrip("-")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        whole = ",".join(groups + [tail])
    return f"{'-' if neg else ''}₹ {whole}.{frac} crore"
