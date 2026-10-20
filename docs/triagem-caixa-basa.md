# Triagem da caixa basa@ — implantação

## 1. Caixa (admin do Microsoft 365)
1. Criar a caixa compartilhada `basa@fonsecabrasilserrao.com` (Exchange admin center → Recipients → Mailboxes → Add a shared mailbox). Caixa compartilhada não usa licença.
2. Dar acesso de leitura a quem coordena o contrato (Full Access), se quiserem abrir a caixa no Outlook.

## 2. App de leitura (Entra ID)
1. Entra admin center → App registrations → New registration: `Aguia Peregrina - Triagem` (single tenant).
2. API permissions → Microsoft Graph → **Application permissions** → `Mail.Read` → *Grant admin consent*.
3. Certificates & secrets → New client secret (validade 12 meses; anotar a data de troca).
4. **Restringir o app só à caixa basa@** (sem isso ele leria todas as caixas do escritório), no Exchange Online PowerShell:
   ```powershell
   New-DistributionGroup -Name "Triagem BASA - app" -Type Security -Members basa@fonsecabrasilserrao.com
   New-ApplicationAccessPolicy -AppId <CLIENT_ID> -PolicyScopeGroupId "Triagem BASA - app" -AccessRight RestrictAccess -Description "Triagem só lê a caixa BASA"
   Test-ApplicationAccessPolicy -AppId <CLIENT_ID> -Identity gustavo@fonsecabrasilserrao.com   # deve dar AccessCheckResult: Denied
   Test-ApplicationAccessPolicy -AppId <CLIENT_ID> -Identity basa@fonsecabrasilserrao.com      # deve dar Granted
   ```

## 3. Railway (serviço worker e web)
`TRIAGEM_CAIXA=basa@fonsecabrasilserrao.com`, `MSGRAPH_TENANT_ID`, `MSGRAPH_CLIENT_ID`, `MSGRAPH_CLIENT_SECRET`. O worker lê a caixa a cada 30 min (`TRIAGEM_INTERVALO_MIN`); na primeira vez, os últimos 30 dias.

## 4. Pessoas por papel
No painel `/painel/triagem` → "Pessoas por papel": coordenacao, financeiro, equipe_pa, equipe_am, prazos_pa, prazos_am.

## 5. Pedir ao BASA (e aos tribunais) para usar só a caixa
- CCONS/GEJUR: passar a enviar tudo do contrato FB1798 para basa@, sem cópias individuais.
- PROJUDI/PJe: cadastrar basa@ como e-mail de notificação dos processos do Banco.

O sistema não envia, move nem apaga e-mails; só lê e monta o resumo por pessoa.
