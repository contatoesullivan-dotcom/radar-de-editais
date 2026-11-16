"""Consulta experimental do PNCP (API oficial), filtrada por termos de comunicação.

Coleta propostas do Ceará com prazo final nos próximos 60 dias, nas
modalidades pregão eletrônico, concorrência eletrônica e dispensa.
A consulta é limitada às primeiras páginas: NÃO é varredura exaustiva.
"""
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = "https://pncp.gov.br/api/consulta/v1/contratacoes/proposta"
MODALIDADES = (6, 4, 8)
MAX_PAGES_PER_MODALITY = 3
PAGE_SIZE = 50
MAX_MATCHES = 60

def collect_pncp(source, now, normalize, comms_regex, fetch_json=None):
    if fetch_json is None:
        fetch_json = download_json
    final_date = (datetime.now(timezone.utc).date() + timedelta(days=60)).strftime("%Y%m%d")
    results = {}
    for mode in MODALIDADES:
        for page in range(1, MAX_PAGES_PER_MODALITY + 1):
            params = {
                "dataFinal": final_date, "codigoModalidadeContratacao": mode,
                "uf": "CE", "pagina": page, "tamanhoPagina": PAGE_SIZE,
            }
            records = fetch_json(BASE + "?" + urllib.parse.urlencode(params))
            if not isinstance(records, dict) or not isinstance(records.get("data"), list):
                raise ValueError("PNCP retornou dados em formato inesperado")
            for row in records["data"]:
                if not isinstance(row, dict):
                    continue
                obj = str(row.get("objetoCompra") or "").strip()
                if len(obj) < 15 or not comms_regex.search(normalize(obj)):
                    continue
                cnpj = str((row.get("orgaoEntidade") or {}).get("cnpj") or "")
                ano = row.get("anoCompra")
                seq = row.get("sequencialCompra")
                if not (cnpj.isdigit() and len(cnpj) == 14 and ano and seq):
                    continue
                url = "https://pncp.gov.br/app/editais/%s/%s/%s" % (cnpj, ano, seq)
                key = str(row.get("numeroControlePNCP") or url)
                ident = "pncp-" + hashlib.sha256(key.encode()).hexdigest()[:14]
                issuer = str((row.get("orgaoEntidade") or {}).get("razaoSocial") or "Órgão público")
                date_pub = row.get("dataPublicacaoPncp")
                date_end = row.get("dataEncerramentoProposta")
                published_at = str(date_pub)[:10] if date_pub else None
                deadline_at = str(date_end)[:10] if date_end else None
                val = row.get("valorTotalEstimado")
                results[url] = {
                    "id": ident,
                    "title": ("Contratação: " + obj[:195])[:215],
                    "issuer": issuer,
                    "category": "servicos",
                    "event_type": "Contratação pública",
                    "published_at": published_at,
                    "deadline_at": deadline_at,
                    "participant": "Conferir edital e modalidade",
                    "location": "CE",
                    "summary": "Objeto informado no PNCP: " + obj[:450] +
                               ". Confira edital, itens, requisitos e prazo na fonte.",
                    "status": "Prazo informado pelo PNCP; confirmar no edital",
                    "official_url": url,
                    "source_id": "pncp",
                    "relevance": "alta",
                    "estimated_value_brl": val if isinstance(val, (int, float)) else None,
                    "confirmed": ["objeto na API PNCP", "órgão", "link PNCP"],
                    "needs_verification": ["habilitação", "itens", "prazo vigente", "valor final"],
                    "first_seen_at": now,
                    "last_seen_at": now,
                }
                if len(results) >= MAX_MATCHES:
                    return list(results.values())
            if page >= int(records.get("totalPaginas") or 0) or len(records["data"]) < PAGE_SIZE:
                break
            if fetch_json is download_json:
                time.sleep(0.7)
    return list(results.values())

def download_json(url):
    request = urllib.request.Request(
        url, headers={"Accept": "application/json",
                      "User-Agent": "RadarDeEditais/1.1 (dados publicos PNCP)"})
    with urllib.request.urlopen(request, timeout=25) as response:
        if response.status == 204:
            return {"data": [], "totalPaginas": 0}
        return json.loads(response.read(6_000_000).decode("utf-8"))
