"""Recebíveis do contrato BASA FB1798: prestação enviada → conferida → NF → paga, por UF.

Regras do contrato usadas aqui:
- cl. 17ª: documentos dos atos até o último dia do mês trabalhado (prazo de envio = fim do mês);
- cl. 18ª: pagamento até o 10º dia útil do mês subsequente ao da prestação, após análise e
  aprovação (o "vencimento contratual" abaixo).

O lançamento das datas é manual (a equipe marca no painel). Este módulo só deriva situação,
alertas e a minuta de cobrança — nunca envia nada: a minuta é texto para alguém revisar e mandar.

Dias úteis = dias úteis bancários em Belém: feriados nacionais, Carnaval (seg/ter), Sexta-feira
Santa, Corpus Christi, Adesão do Pará (15/08) e os municipais de Belém (12/01 e 08/12).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from typing import Any

UFS_COM_NF_PROPRIA = ("PA", "AM")  # o BASA paga PA e AM em NFs separadas
OUTRAS = "OU"  # atos avulsos de outras UFs (AC, GO, RO...) numa linha só
PRAZO_CONFERENCIA_DU = 5  # BASA parado na conferência além disso → follow-up
PRAZO_NF_DU = 2  # conferido e sem NF além disso → lembrete interno
AVISO_VENCIMENTO_DU = 3

_MESES = (
    "janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro"
).split()


def _pascoa(ano: int) -> date:
    a, b, c = ano % 19, ano // 100, ano % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 22 * m) // 451
    mes = (h + m - 7 * n + 114) // 31
    dia = (h + m - 7 * n + 114) % 31 + 1
    return date(ano, mes, dia)


@lru_cache
def feriados(ano: int) -> frozenset[date]:
    fixos = [
        (1, 1),
        (1, 12),  # aniversário de Belém
        (4, 21),
        (5, 1),
        (8, 15),  # adesão do Pará
        (9, 7),
        (10, 12),
        (11, 2),
        (11, 15),
        (11, 20),
        (12, 8),  # N. Sra. da Conceição (Belém)
        (12, 25),
    ]
    p = _pascoa(ano)
    moveis = [
        p - timedelta(days=48),
        p - timedelta(days=47),
        p - timedelta(days=2),
        p + timedelta(days=60),
    ]
    return frozenset([date(ano, m, d) for m, d in fixos] + moveis)


def dia_util(d: date) -> bool:
    return d.weekday() < 5 and d not in feriados(d.year)


def dias_uteis_entre(inicio: date, fim: date) -> int:
    """Dias úteis em (inicio, fim]; negativo se fim < inicio."""
    if fim < inicio:
        return -dias_uteis_entre(fim, inicio)
    n, d = 0, inicio
    while d < fim:
        d += timedelta(days=1)
        n += dia_util(d)
    return n


def n_esimo_dia_util(ano: int, mes: int, n: int) -> date:
    d, k = date(ano, mes, 1), 0
    while True:
        if dia_util(d):
            k += 1
            if k == n:
                return d
        d += timedelta(days=1)


def fim_do_mes(competencia: str) -> date:
    a, m = (int(x) for x in competencia.split("-"))
    return date(a + (m == 12), m % 12 + 1, 1) - timedelta(days=1)


def vencimento_contratual(competencia: str) -> date:
    a, m = (int(x) for x in competencia.split("-"))
    return n_esimo_dia_util(a + (m == 12), m % 12 + 1, 10)


def grupo_uf(uf: str | None) -> str:
    u = (uf or "").upper()[:2]
    return u if u in UFS_COM_NF_PROPRIA else OUTRAS


def rotulo_uf(uf: str) -> str:
    return "outras UFs" if uf == OUTRAS else uf


def competencia_extenso(competencia: str) -> str:
    a, m = (int(x) for x in competencia.split("-"))
    return f"{_MESES[m - 1]}/{a}"


@dataclass
class Recebivel:
    competencia: str
    uf: str
    valor_faturavel: float | None = None  # Anexo II da pré-auditoria
    valor_declarado: float | None = None
    enviado_em: date | None = None
    conferido_em: date | None = None
    valor_aprovado: float | None = None
    nf_numero: str | None = None
    nf_emitida_em: date | None = None
    nf_valor: float | None = None
    pago_em: date | None = None
    valor_pago: float | None = None


@dataclass
class Alerta:
    codigo: str
    nivel: str  # alto | medio | info
    texto: str


@dataclass
class Situacao:
    etapa: str  # A_ENVIAR | ENVIADA | CONFERIDA | NF_EMITIDA | PAGA
    vencimento: date
    dias_uteis_para_vencer: int | None  # negativo = vencido; None se pago
    em_aberto: float
    alertas: list[Alerta] = field(default_factory=list)
    minuta: str | None = None  # quando há o que cobrar do Banco

    def as_dict(self) -> dict[str, Any]:
        return {
            "etapa": self.etapa,
            "vencimento": self.vencimento.isoformat(),
            "dias_uteis_para_vencer": self.dias_uteis_para_vencer,
            "em_aberto": round(self.em_aberto, 2),
            "alertas": [a.__dict__ for a in self.alertas],
            "minuta": self.minuta,
        }


def _brl(v: float | None) -> str:
    if v is None:
        return "—"
    s = f"{v:,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _dt(d: date | None) -> str:
    return d.strftime("%d/%m/%Y") if d else "—"


def situacao(r: Recebivel, hoje: date) -> Situacao:
    venc = vencimento_contratual(r.competencia)
    if r.pago_em:
        etapa = "PAGA"
    elif r.nf_emitida_em:
        etapa = "NF_EMITIDA"
    elif r.conferido_em:
        etapa = "CONFERIDA"
    elif r.enviado_em:
        etapa = "ENVIADA"
    else:
        etapa = "A_ENVIAR"
    devido = r.nf_valor or r.valor_aprovado or r.valor_faturavel or 0.0
    em_aberto = 0.0 if r.pago_em else devido
    if r.pago_em and r.valor_pago is not None:
        em_aberto = max(devido - r.valor_pago, 0.0)
    du = None if r.pago_em else dias_uteis_entre(hoje, venc)
    s = Situacao(etapa, venc, du, em_aberto)
    al = s.alertas

    fim = fim_do_mes(r.competencia)
    if etapa == "A_ENVIAR" and hoje > fim:
        al.append(
            Alerta(
                "ENVIO_ATRASADO", "alto", f"prestação não enviada; prazo era {_dt(fim)} (cl. 17ª)"
            )
        )
    if r.enviado_em and r.enviado_em > fim + timedelta(days=5):
        al.append(
            Alerta(
                "ENVIADA_FORA_DO_PRAZO",
                "info",
                f"enviada em {_dt(r.enviado_em)}, após o fim do mês",
            )
        )
    if etapa == "ENVIADA" and r.enviado_em:
        parado = dias_uteis_entre(r.enviado_em, hoje)
        if parado > PRAZO_CONFERENCIA_DU:
            al.append(
                Alerta(
                    "CONFERENCIA_PARADA",
                    "medio",
                    f"BASA sem retorno da conferência há {parado} dias úteis",
                )
            )
    if etapa == "CONFERIDA" and r.conferido_em:
        parado = dias_uteis_entre(r.conferido_em, hoje)
        if parado > PRAZO_NF_DU:
            al.append(
                Alerta(
                    "EMITIR_NF",
                    "medio",
                    f"conferida há {parado} dias úteis e sem NF emitida (interno)",
                )
            )
    if (
        r.valor_aprovado is not None
        and r.valor_faturavel
        and r.valor_aprovado < r.valor_faturavel - 0.01
    ):
        al.append(
            Alerta(
                "GLOSA",
                "medio",
                f"aprovado {_brl(r.valor_aprovado)} contra {_brl(r.valor_faturavel)} faturável: "
                f"glosa de {_brl(r.valor_faturavel - r.valor_aprovado)} — "
                "pedir a lista dos atos glosados",
            )
        )
    if r.pago_em and r.valor_pago is not None and devido and r.valor_pago < devido - 0.01:
        al.append(
            Alerta(
                "PAGO_A_MENOR",
                "alto",
                f"pago {_brl(r.valor_pago)} de {_brl(devido)}: falta {_brl(devido - r.valor_pago)}",
            )
        )
    if du is not None and etapa != "A_ENVIAR":
        if du < 0:
            al.append(
                Alerta(
                    "VENCIDO",
                    "alto",
                    f"vencido há {-du} dias úteis (10º dia útil = {_dt(venc)}, cl. 18ª)",
                )
            )
        elif du <= AVISO_VENCIMENTO_DU:
            al.append(
                Alerta("VENCE_EM_BREVE", "info", f"vence em {du} dia(s) útil(eis), {_dt(venc)}")
            )

    codigos = {a.codigo for a in al}
    if "PAGO_A_MENOR" in codigos or ("VENCIDO" in codigos and etapa == "NF_EMITIDA"):
        s.minuta = minuta_cobranca(r, s)
    elif etapa == "ENVIADA" and codigos & {"VENCIDO", "CONFERENCIA_PARADA"}:
        s.minuta = minuta_conferencia(r, s)
    # CONFERIDA sem NF: a pendência é interna (emitir a NF), não há o que cobrar do Banco
    return s


def _cabecalho_minuta(r: Recebivel, assunto: str) -> list[str]:
    return [
        "RASCUNHO — revisar antes de enviar (o sistema não envia e-mails).",
        "Para: Jurídico CCONS / GEJUR — Banco da Amazônia (confirmar o responsável pela UF)",
        f"Assunto: Contrato FB1798 — {assunto} — {competencia_extenso(r.competencia)} — "
        f"{rotulo_uf(r.uf)}",
        "",
        "Prezados,",
        "",
    ]


def minuta_conferencia(r: Recebivel, s: Situacao | None = None) -> str:
    linhas = _cabecalho_minuta(r, "conferência da prestação de contas")
    linhas += [
        f"Encaminhamos em {_dt(r.enviado_em)} o relatório de atos processuais de "
        f"{competencia_extenso(r.competencia)} referente aos processos de {rotulo_uf(r.uf)} "
        f"(Anexo II, total de {_brl(r.valor_faturavel)}), com os documentos comprobatórios "
        "anexados ao Benner.",
        "",
        "Solicitamos, por gentileza, a conclusão da análise de conformidade para emissão da nota "
        "fiscal, nos termos da Cláusula Décima Oitava"
        + (
            f", cujo prazo de pagamento (10º dia útil, {_dt(s.vencimento)}) já transcorreu"
            if s and s.dias_uteis_para_vencer is not None and s.dias_uteis_para_vencer < 0
            else ""
        )
        + ". Havendo apontamentos sobre algum ato, pedimos que sejam indicados processo e ato "
        "para pronta regularização.",
        "",
        "Atenciosamente,",
        "Fonseca Brasil Serrão Advogados",
    ]
    return "\n".join(linhas)


def minuta_cobranca(r: Recebivel, s: Situacao) -> str:
    linhas = _cabecalho_minuta(r, "pagamento em aberto")
    nf = f"Nota Fiscal nº {r.nf_numero}" if r.nf_numero else "a nota fiscal"
    linhas += [
        f"Referente aos serviços de {competencia_extenso(r.competencia)} ({rotulo_uf(r.uf)}), "
        f"{nf}, emitida em {_dt(r.nf_emitida_em)}, no valor de {_brl(r.nf_valor or s.em_aberto)}"
        + (f", conferida pela CCONS em {_dt(r.conferido_em)}" if r.conferido_em else "")
        + ".",
        "",
        f"Pela Cláusula Décima Oitava do contrato, o pagamento deveria ocorrer até o 10º dia útil "
        f"do mês subsequente ({_dt(s.vencimento)}). Até esta data consta em aberto "
        f"{_brl(s.em_aberto)}.",
        "",
        "Solicitamos a confirmação da data prevista para o crédito ou a indicação de eventual "
        "pendência que esteja impedindo o pagamento, para que possamos saná-la de imediato.",
        "",
        "Atenciosamente,",
        "Fonseca Brasil Serrão Advogados",
    ]
    return "\n".join(linhas)
