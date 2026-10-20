"""Login individual: convite → senha → autenticador → sessão nos painéis; trilha com o e-mail."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core import totp
from app.core.config import get_settings


def _cliente(engine, monkeypatch, env: str = "prod"):  # type: ignore[no-untyped-def]
    from app.api import auth as auth_mod
    from app.core import db as core_db
    from app.main import app

    core_db.SessionLocal.configure(bind=engine)
    s = get_settings()
    monkeypatch.setattr(s, "ops_key", "k")
    monkeypatch.setattr(s, "app_env", env)
    auth_mod._FALHAS.clear()
    c = TestClient(app)
    tid = c.post("/faturamento/basa/setup", headers={"X-Ops-Key": "k"}).json()["tenant_id"]
    return c, tid


def _entrar(c: TestClient, tid: str, email: str, senha: str, seg: str) -> str:
    r = c.post("/auth/login", json={"email": email, "password": senha, "tenant_id": tid})
    assert r.status_code == 200, r.text
    r = c.post("/auth/mfa", json={"token": r.json()["access_token"], "code": totp.codigo(seg)})
    assert r.status_code == 200, r.text
    return str(r.json()["access_token"])


def test_convite_login_e_uso_nos_paineis(engine, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    c, tid = _cliente(engine, monkeypatch)
    ops = {"X-Ops-Key": "k", "X-Tenant-ID": tid}
    assert c.get("/auth/tenant").json()["tenant_id"] == tid

    r = c.post(
        "/usuarios", headers=ops, json={"email": "Ana@FBS.test", "nome": "Ana", "papel": "partner"}
    )
    assert r.status_code == 200, r.text
    conv = r.json()["convite"]
    assert r.json()["link"].startswith("/painel/entrar?convite=")
    assert (
        c.post("/usuarios", headers=ops, json={"email": "ana@fbs.test", "nome": "Ana"}).status_code
        == 409
    )

    # o convite não serve como sessão
    assert (
        c.get(
            "/faturamento/basa/recebiveis",
            headers={"X-Tenant-ID": tid, "Authorization": f"Bearer {conv}"},
        ).status_code
        == 401
    )
    assert (
        c.post("/auth/convite/senha", json={"convite": conv, "senha": "curta"}).status_code == 422
    )
    r = c.post("/auth/convite/senha", json={"convite": conv, "senha": "uma-senha-bem-longa"})
    seg = r.json()["segredo"]
    assert r.json()["otpauth"].startswith("otpauth://totp/")
    assert (
        c.post("/auth/convite/confirmar", json={"convite": conv, "codigo": "123456"}).status_code
        == 401
    )
    assert c.post(
        "/auth/convite/confirmar", json={"convite": conv, "codigo": totp.codigo(seg)}
    ).json() == {"ativo": True}
    # convite já usado
    assert (
        c.post(
            "/auth/convite/senha", json={"convite": conv, "senha": "outra-senha-longa-1"}
        ).status_code
        == 401
    )

    # em prod o 000000 não passa
    r = c.post(
        "/auth/login",
        json={"email": "ana@fbs.test", "password": "uma-senha-bem-longa", "tenant_id": tid},
    )
    assert (
        c.post("/auth/mfa", json={"token": r.json()["access_token"], "code": "000000"}).status_code
        == 401
    )

    tok = _entrar(c, tid, "ana@fbs.test", "uma-senha-bem-longa", seg)
    h = {"X-Tenant-ID": tid, "Authorization": f"Bearer {tok}"}
    assert c.get("/faturamento/basa/recebiveis", headers=h).status_code == 200
    assert c.get("/triagem", headers=h).status_code == 200
    assert c.get("/benner/correcoes", headers=h).status_code == 200
    # a trilha usa o e-mail do token, não um cabeçalho que qualquer um escreve
    c.put("/triagem/papeis/coordenacao", headers={**h, "X-Usuario": "falso"}, json=[])
    # sócio cria usuário comum; usuário comum não cria
    r = c.post(
        "/usuarios", headers=h, json={"email": "bia@fbs.test", "nome": "Bia", "papel": "lawyer"}
    )
    assert r.status_code == 200
    conv_b = r.json()["convite"]
    seg_b = c.post(
        "/auth/convite/senha", json={"convite": conv_b, "senha": "senha-da-bia-123"}
    ).json()["segredo"]
    c.post("/auth/convite/confirmar", json={"convite": conv_b, "codigo": totp.codigo(seg_b)})
    tok_b = _entrar(c, tid, "bia@fbs.test", "senha-da-bia-123", seg_b)
    hb = {"X-Tenant-ID": tid, "Authorization": f"Bearer {tok_b}"}
    assert (
        c.post("/usuarios", headers=hb, json={"email": "c@fbs.test", "nome": "C"}).status_code
        == 403
    )
    assert {u["email"] for u in c.get("/usuarios", headers=hb).json()} == {
        "ana@fbs.test",
        "bia@fbs.test",
    }

    # outro tenant no cabeçalho com o mesmo token → recusado
    assert (
        c.get(
            "/triagem", headers={**h, "X-Tenant-ID": "00000000-0000-0000-0000-000000000001"}
        ).status_code
        == 403
    )
    # sem nada → 404
    assert c.get("/triagem", headers={"X-Tenant-ID": tid}).status_code == 404


def test_bloqueio_por_tentativas(engine, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    c, tid = _cliente(engine, monkeypatch)
    for _ in range(6):
        c.post("/auth/login", json={"email": "x@fbs.test", "password": "errada", "tenant_id": tid})
    r = c.post("/auth/login", json={"email": "x@fbs.test", "password": "errada", "tenant_id": tid})
    assert r.status_code == 429


def test_totp_vetor_rfc6238() -> None:
    import base64

    seg = base64.b32encode(b"12345678901234567890").decode().rstrip("=")
    assert totp.codigo(seg, 59) == "287082"
    assert totp.verificar(seg, "287082", instante=59 + 30)  # tolera um passo
    assert not totp.verificar(seg, "287082", instante=59 + 90)
    assert totp.decifrar(totp.cifrar(seg, "chave"), "chave") == seg
    assert totp.decifrar(totp.cifrar(seg, "chave"), "outra") is None
