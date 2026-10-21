// Sessão dos painéis: login individual (e-mail + senha + código do autenticador).
// A chave de operação continua como acesso técnico (link discreto na tela de login).
(function () {
  const ss = {
    get(k) { try { return sessionStorage.getItem(k) } catch (e) { return null } },
    set(k, v) { try { sessionStorage.setItem(k, v) } catch (e) {} },
    del(k) { try { sessionStorage.removeItem(k) } catch (e) {} },
  };
  const ls = {
    get(k) { try { return localStorage.getItem(k) } catch (e) { return null } },
    set(k, v) { try { localStorage.setItem(k, v) } catch (e) {} },
  };
  const S = {
    tok: ss.get("tok"), chave: ss.get("k"), tenant: ss.get("t"), email: ss.get("email") || ls.get("u") || "",
    headers() {
      const h = { "X-Tenant-ID": S.tenant || "", "Content-Type": "application/json" };
      if (S.tok) h["Authorization"] = "Bearer " + S.tok;
      else if (S.chave) { h["X-Ops-Key"] = S.chave; h["X-Usuario"] = S.email; }
      return h;
    },
    async api(p, o = {}) {
      const h = { ...S.headers(), ...(o.headers || {}) };
      if (o.body instanceof FormData) delete h["Content-Type"];  // o navegador põe o boundary
      const r = await fetch(p, { ...o, headers: h });
      if (r.status === 401) { ss.del("tok"); S.tok = null; throw new Error("sessão expirada — entre de novo"); }
      if (!r.ok) throw new Error(r.status + " " + (await r.text()));
      return (r.headers.get("content-type") || "").includes("json") ? r.json() : r.blob();
    },
    sair() { ["tok", "k", "t", "email"].forEach(ss.del); location.reload(); },
    async iniciar(pronto) {
      const L = document.getElementById("login"), A = document.getElementById("app");
      const mostrar = async () => {
        L.hidden = true; A.hidden = false;
        try { await pronto(); } catch (e) { ["tok", "k"].forEach(ss.del); S.tok = S.chave = null; A.hidden = true; formulario("Sessão expirada: entre de novo."); }
      };
      const formulario = (msg) => {
        L.hidden = false;
        L.innerHTML = `<label>E-mail<input id="s_email" type="email" autocomplete="username" required value="${S.email}"></label>
          <label>Senha<input id="s_senha" type="password" autocomplete="current-password" required></label>
          <label id="s_l_cod" hidden>Código do autenticador<input id="s_cod" inputmode="numeric" autocomplete="one-time-code" maxlength="6"></label>
          <button class="pri" id="s_ok">Entrar</button><span class="mut" id="s_erro">${msg || ""}</span>
          <span class="mut"><a href="#" id="s_tec">acesso técnico (chave de operação)</a></span>`;
        let pre = null;
        L.onsubmit = async (e) => {
          e.preventDefault(); const erro = document.getElementById("s_erro"); erro.textContent = "";
          try {
            if (!S.tenant) { const r = await fetch("/auth/tenant"); S.tenant = (await r.json()).tenant_id; }
            S.email = document.getElementById("s_email").value.trim().toLowerCase();
            if (document.getElementById("s_tec").dataset.on) {
              S.chave = document.getElementById("s_senha").value.trim(); S.tok = null;
              ss.set("k", S.chave); ss.set("t", S.tenant); ss.set("email", S.email); ls.set("u", S.email); return mostrar();
            }
            if (!pre) {
              const r = await fetch("/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: S.email, password: document.getElementById("s_senha").value, tenant_id: S.tenant }) });
              if (!r.ok) throw new Error(r.status === 429 ? "muitas tentativas; aguarde 15 minutos" : "e-mail ou senha inválidos");
              pre = (await r.json()).access_token;
              document.getElementById("s_l_cod").hidden = false; document.getElementById("s_cod").focus(); return;
            }
            const r = await fetch("/auth/mfa", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ token: pre, code: document.getElementById("s_cod").value }) });
            if (!r.ok) { if (r.status === 401 && (await r.text()).includes("expirado")) pre = null; throw new Error("código inválido"); }
            S.tok = (await r.json()).access_token; S.chave = null;
            ss.set("tok", S.tok); ss.set("t", S.tenant); ss.set("email", S.email); ls.set("u", S.email); ss.del("k");
            mostrar();
          } catch (err) { erro.textContent = err.message; }
        };
        document.getElementById("s_tec").onclick = (e) => {
          e.preventDefault(); e.target.dataset.on = "1";
          document.querySelector("#login label:nth-of-type(2)").firstChild.textContent = "Chave de operação";
          e.target.textContent = "usando a chave de operação";
        };
      };
      if (S.tok || S.chave) return mostrar();
      formulario();
    },
  };
  window.Sessao = S;
})();
