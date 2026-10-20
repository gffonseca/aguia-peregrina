from __future__ import annotations

import functools
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.litigation import Thesis, ThesisVersion
from app.modules.m00_playbook.schema import (
    Playbook,
    PlaybookStatus,
    load_playbook,
    to_thesis_payloads,
)

PLAYBOOKS_DIR = Path(__file__).resolve().parents[3] / "playbooks"


def create_version(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    thesis: Thesis,
    body_markdown: str,
    conditions: dict,
    author_user_id: uuid.UUID,
    author_oab: str,
) -> ThesisVersion:
    last = db.scalar(
        select(ThesisVersion.version)
        .where(ThesisVersion.thesis_id == thesis.id)
        .order_by(ThesisVersion.version.desc())
        .limit(1)
    )
    version = ThesisVersion(
        tenant_id=tenant_id,
        thesis_id=thesis.id,
        version=(last or 0) + 1,
        body_markdown=body_markdown,
        conditions=conditions,
        author_user_id=author_user_id,
        author_oab=author_oab,
    )
    db.add(version)
    return version


def approve_version(
    version: ThesisVersion,
    *,
    approver_user_id: uuid.UUID | None,
    approver_oab: str,
    approved_at: datetime | None = None,
) -> None:
    """Só sócio/advogado com OAB aprova; a aprovação torna a versão a corrente."""
    if not approver_oab:
        raise PermissionError("aprovação de tese exige OAB")
    version.approved_by_user_id = approver_user_id
    version.approved_by_oab = approver_oab
    version.approved_at = approved_at or datetime.now(UTC)


# ---------------------------------------------------------------------------
# Arquivos de playbook no repositório
# ---------------------------------------------------------------------------


def playbook_path(name: str) -> Path:
    """`consignado-rmc-tjpa` → playbooks/consignado-rmc-tjpa.playbook.yaml (sem path traversal)."""
    safe = Path(name).name.removesuffix(".yaml").removesuffix(".playbook")
    return PLAYBOOKS_DIR / f"{safe}.playbook.yaml"


@functools.lru_cache(maxsize=16)
def playbook_for_typology(typology: str | None) -> Playbook | None:
    """Encontra o playbook cuja `metadata.tipologia` casa com a tipologia do caso.

    Aceita a família: `consignado` casa `consignado_rmc_nao_reconhecido`. Prefere o
    playbook aprovado; entre vários, o de maior versão.
    """
    if not typology:
        return None
    candidates: list[Playbook] = []
    for path in sorted(PLAYBOOKS_DIR.glob("*.playbook.yaml")):
        try:
            pb = load_playbook(path)
        except Exception:  # noqa: BLE001 - rascunhos inválidos não derrubam a busca
            continue
        tip = pb.metadata.tipologia
        if tip == typology or tip.startswith(typology + "_") or typology.startswith(tip + "_"):
            candidates.append(pb)
    if not candidates:
        return None
    candidates.sort(
        key=lambda p: (p.metadata.status == PlaybookStatus.aprovado, p.metadata.versao),
        reverse=True,
    )
    return candidates[0]


def typology_matches(case_typology: str | None, thesis_typology: str) -> bool:
    if not case_typology:
        return False
    return (
        thesis_typology == case_typology
        or thesis_typology.startswith(case_typology + "_")
        or case_typology.startswith(thesis_typology + "_")
    )


# ---------------------------------------------------------------------------
# Carga do playbook em theses / thesis_versions (M0)
# ---------------------------------------------------------------------------


def load_playbook_into_tenant(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    pb: Playbook,
    author_user_id: uuid.UUID,
    approver_user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Idempotente: uma versão por (tipologia, código, playbook_id, playbook_versao).

    Se o playbook está `aprovado`, a versão é aprovada com a OAB e o timestamp do YAML
    (aprovação feita fora da máquina, pelo advogado-dono); se não, fica como rascunho.
    """
    payloads = to_thesis_payloads(pb)
    created, reused, approved = 0, 0, 0
    by_code: dict[str, Thesis] = {}
    # pais antes dos filhos (T06 antes de T06.1)
    for item in sorted(payloads, key=lambda i: (i["code"].count("."), i["code"])):
        thesis = db.scalar(
            select(Thesis).where(Thesis.typology == item["typology"], Thesis.code == item["code"])
        )
        if thesis is None:
            thesis = Thesis(
                tenant_id=tenant_id,
                typology=item["typology"],
                code=item["code"],
                title=item["title"],
                parent_id=by_code[item["parent_code"]].id if item.get("parent_code") else None,
            )
            db.add(thesis)
            db.flush()
        else:
            thesis.title = item["title"]
            thesis.is_active = True
        by_code[item["code"]] = thesis

        existing = None
        for v in db.scalars(select(ThesisVersion).where(ThesisVersion.thesis_id == thesis.id)):
            c = v.conditions or {}
            if (
                c.get("playbook_id") == pb.metadata.id
                and c.get("playbook_versao") == pb.metadata.versao
            ):
                existing = v
                break
        if existing is not None:
            reused += 1
            version = existing
        else:
            version = create_version(
                db,
                tenant_id=tenant_id,
                thesis=thesis,
                body_markdown=item["body_markdown"],
                conditions=item["conditions"],
                author_user_id=author_user_id,
                author_oab=item["author_oab"],
            )
            db.flush()
            created += 1
        if pb.metadata.status == PlaybookStatus.aprovado and version.approved_at is None:
            approve_version(
                version,
                approver_user_id=approver_user_id,
                approver_oab=pb.metadata.aprovado_por_oab or "",
                approved_at=pb.metadata.aprovado_em,
            )
            approved += 1
        if version.approved_at is not None:
            thesis.current_version_id = version.id
    return {
        "playbook_id": pb.metadata.id,
        "versao": pb.metadata.versao,
        "status": pb.metadata.status.value,
        "typology": pb.metadata.tipologia,
        "theses": len(payloads),
        "versions_created": created,
        "versions_reused": reused,
        "versions_approved_now": approved,
        "approved_by_oab": pb.metadata.aprovado_por_oab,
    }


def approved_theses(
    db: Session, *, case_typology: str | None
) -> list[tuple[Thesis, ThesisVersion]]:
    """Teses ativas com versão corrente aprovada por OAB para a tipologia (ou família)."""
    out: list[tuple[Thesis, ThesisVersion]] = []
    for thesis in db.scalars(select(Thesis).where(Thesis.is_active.is_(True))):
        if not typology_matches(case_typology, thesis.typology) or not thesis.current_version_id:
            continue
        version = db.get(ThesisVersion, thesis.current_version_id)
        if version is None or version.approved_at is None or not version.approved_by_oab:
            continue
        out.append((thesis, version))
    out.sort(key=lambda tv: (tv[1].conditions or {}).get("ordem", 999))
    return out


__all__ = [
    "PLAYBOOKS_DIR",
    "approve_version",
    "approved_theses",
    "create_version",
    "load_playbook_into_tenant",
    "playbook_for_typology",
    "playbook_path",
    "typology_matches",
]
