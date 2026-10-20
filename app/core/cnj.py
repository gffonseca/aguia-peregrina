"""Número único do CNJ (Res. CNJ 65/2008): NNNNNNN-DD.AAAA.J.TR.OOOO.

Decodifica segmento de justiça (J), tribunal (TR) e foro/unidade de origem (OOOO) e
valida o dígito verificador (módulo 97, ISO 7064). Usado para derivar `court`,
segmento e comarca sem depender de tabelas de lookup externas (os endpoints de
lookup do Legal One respondem 404).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_DIGITS = re.compile(r"\D+")

SEGMENTS: dict[int, str] = {
    1: "STF",
    2: "CNJ",
    3: "STJ",
    4: "federal",
    5: "trabalhista",
    6: "eleitoral",
    7: "militar_uniao",
    8: "estadual",
    9: "militar_estadual",
}

# TR da Justiça Estadual (segmento 8) e Eleitoral (6) → UF
UF_BY_TR: dict[int, str] = {
    1: "AC",
    2: "AL",
    3: "AP",
    4: "AM",
    5: "BA",
    6: "CE",
    7: "DF",
    8: "ES",
    9: "GO",
    10: "MA",
    11: "MT",
    12: "MS",
    13: "MG",
    14: "PA",
    15: "PB",
    16: "PR",
    17: "PE",
    18: "PI",
    19: "RJ",
    20: "RN",
    21: "RS",
    22: "RO",
    23: "RR",
    24: "SC",
    25: "SE",
    26: "SP",
    27: "TO",
}


@dataclass(frozen=True)
class CNJ:
    sequential: str  # NNNNNNN
    check_digit: str  # DD
    year: int  # AAAA
    segment: int  # J
    tribunal: int  # TR
    origin: str  # OOOO (foro / vara de origem)

    @property
    def formatted(self) -> str:
        return (
            f"{self.sequential}-{self.check_digit}.{self.year:04d}."
            f"{self.segment}.{self.tribunal:02d}.{self.origin}"
        )

    @property
    def digits(self) -> str:
        return (
            f"{self.sequential}{self.check_digit}{self.year:04d}"
            f"{self.segment}{self.tribunal:02d}{self.origin}"
        )

    @property
    def segment_name(self) -> str:
        return SEGMENTS.get(self.segment, "desconhecido")

    @property
    def uf(self) -> str | None:
        if self.segment in (8, 6, 9):
            return UF_BY_TR.get(self.tribunal)
        return None

    @property
    def court(self) -> str:
        """Sigla curta do tribunal (TJPA, TRT8, TRF1, TRE-PA, STJ...)."""
        if self.segment == 8:
            uf = UF_BY_TR.get(self.tribunal)
            return f"TJ{uf}" if uf else f"TJ{self.tribunal:02d}"
        if self.segment == 5:
            return f"TRT{self.tribunal}"
        if self.segment == 4:
            return f"TRF{self.tribunal}"
        if self.segment == 6:
            uf = UF_BY_TR.get(self.tribunal)
            return f"TRE-{uf}" if uf else f"TRE{self.tribunal:02d}"
        if self.segment == 9:
            uf = UF_BY_TR.get(self.tribunal)
            return f"TJM{uf}" if uf else f"TJM{self.tribunal:02d}"
        if self.segment in (1, 2, 3):
            return SEGMENTS[self.segment]
        if self.segment == 7:
            return "STM"
        return f"J{self.segment}-TR{self.tribunal:02d}"

    @property
    def is_valid(self) -> bool:
        return self.check_digit == expected_check_digit(
            self.sequential, self.year, self.segment, self.tribunal, self.origin
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "formatted": self.formatted,
            "year": self.year,
            "segment": self.segment,
            "segment_name": self.segment_name,
            "tribunal": self.tribunal,
            "court": self.court,
            "uf": self.uf,
            "origin": self.origin,
            "valid": self.is_valid,
        }


def expected_check_digit(
    sequential: str, year: int, segment: int, tribunal: int, origin: str
) -> str:
    """DD = 98 − (NNNNNNNAAAAJTROOOO00 mod 97)."""
    base = int(f"{int(sequential):07d}{year:04d}{segment}{tribunal:02d}{int(origin):04d}00")
    return f"{98 - (base % 97):02d}"


def only_digits(raw: str) -> str:
    return _DIGITS.sub("", raw or "")


def parse(raw: str | None) -> CNJ | None:
    """Aceita com ou sem máscara; devolve None se não tiver 20 dígitos."""
    if not raw:
        return None
    d = only_digits(raw)
    if len(d) != 20:
        return None
    return CNJ(
        sequential=d[0:7],
        check_digit=d[7:9],
        year=int(d[9:13]),
        segment=int(d[13]),
        tribunal=int(d[14:16]),
        origin=d[16:20],
    )


def normalize(raw: str | None) -> str | None:
    """Devolve o número no formato padrão com máscara, ou None se não for um CNJ."""
    cnj = parse(raw)
    return cnj.formatted if cnj else None


CNJ_IN_TEXT = re.compile(r"\b\d{7}-?\d{2}\.?\d{4}\.?\d\.?\d{2}\.?\d{4}\b")


def find_in_text(text: str | None) -> list[str]:
    """Extrai números CNJ (com ou sem máscara) de um texto livre, normalizados e sem repetição."""
    if not text:
        return []
    seen: list[str] = []
    for m in CNJ_IN_TEXT.finditer(text):
        n = normalize(m.group(0))
        if n and n not in seen:
            seen.append(n)
    return seen


__all__ = [
    "CNJ",
    "SEGMENTS",
    "UF_BY_TR",
    "expected_check_digit",
    "find_in_text",
    "normalize",
    "only_digits",
    "parse",
]
