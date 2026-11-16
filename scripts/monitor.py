#!/usr/bin/env python3
"""Radar de Editais: coleta cautelosa de links em páginas oficiais.
Sem leitura dos PDFs, não presume prazo, remuneração ou elegibilidade.
Funciona só com a biblioteca padrão do Python (GitHub Actions).
"""
import hashlib
import html
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urldefrag, urljoin, urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data/opportunities.json"
STATUS_FILE = ROOT / "data/monitor_status.json"
SOURCES_FILE = ROOT / "config/sources.json"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")
MAX_PER_SOURCE = 30

def normalize(value):
    txt = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(c for c in txt if not unicodedata.combining(c)).lower()

COMMS = re.compile(
    r"comunic|jornal|imprensa|assessoria|publicid|marketing|"
    r"design|audiovisual|fotograf|cinema|video|midia|conteudo|"
    r"redes sociais|cultura digital|arte digital|documentari|"
    r"producao cultural|memoria|patrimonio cultural"
)
ACADEMIC = re.compile(
    r"mestrad|selec|edital|inscri|turma 20|processo seletiv|"
    r"retific|cronograma|termo aditiv|aluno regular|bolsa"
)
SERVICES = re.compile(
    r"edital|credenc|pregao|licitac|chamada|manifestacao de interesse|"
    r"selec|contratac|resultado|retific|prorrog|aviso"
)
STOP = re.compile(
    r"^(home|inicio|menu|contato|sobre|pesquisa|buscar|"
    r"noticias|eventos|galeria|politica de privacidade|"
    r"acessibilidade|imprensa|conheca|mais informacoes)$"
)
GENERIC = re.compile(
    r"^(confira aqui|clique aqui|saiba mais|acesse|acesse aqui|"
    r"leia mais|ver mais|download|baixar|ver edital|edital|"
    r"documento|arquivo|pdf|aqui|ver processo|detalhes)$"
)
EXCLUDE_EXT = re.compile(r"\.(png|jpg|jpeg|gif|webp|svg|css|js|zip|rar|xlsx?|docx?)(?:$|[?#])", re.I)

class PageLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.last_heading = ""
        self.heading_tag = None
        self.heading_parts = []
        self.anchor_href = None
        self.anchor_parts = []
        self.skip_tag = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style"):
            self.skip_tag = tag
        if self.skip_tag:
            return
        if tag in ("h1", "h2", "h3", "h4", "h5"):
            self.heading_tag = tag
            self.heading_parts = []
        if tag == "a":
            self.anchor_href = attrs.get("href")
            self.anchor_parts = []

    def handle_data(self, data):
        if self.skip_tag:
            return
        if self.heading_tag:
            self.heading_parts.append(data)
        if self.anchor_href is not None:
            self.anchor_parts.append(data)

    def handle_endtag(self, tag):
        if tag == self.skip_tag:
            self.skip_tag = None
            return
        if tag == "a" and self.anchor_href is not None:
            label = " ".join("".join(self.anchor_parts).split())
            self.links.append((self.anchor_href, label, self.last_heading))
            self.anchor_href = None
            self.anchor_parts = []
        if tag == self.heading_tag:
            heading = " ".join("".join(self.heading_parts).split())
            if heading:
                self.last_heading = heading[:280]
            self.heading_tag = None
            self.heading_parts = []

def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def source_title(label, heading, link):
    label = " ".join(html.unescape(label).split()).strip()
    heading = " ".join(html.unescape(heading).split()).strip()
    if GENERIC.match(normalize(label)) or len(label) < 10:
        if 15 <= len(heading) <= 220 and not STOP.match(normalize(heading)):
            return heading
        slug = unquote(urlparse(link).path.rsplit("/", 1)[-1])
        slug = re.sub(r"\.pdf$", "", slug, flags=re.I)
        slug = re.sub(r"[-_]+", " ", slug).strip()
        return slug[:200] if len(slug) >= 14 else ""
    return label[:220]

def relevant(title, source):
    t = normalize(title)
    if STOP.match(t) or len(t) < 13 or len(t) > 220:
        return False
    # Não destacar como novas seleções editais explicitamente datados de anos antigos.
    years = set(re.findall(r"\b20\d{2}\b", t))
    if years and all(int(y) < 2026 for y in years):
        return False
    kind = source.get("kind")
    if kind == "academico":
        return bool(ACADEMIC.search(t))
    if kind in ("licitacoes", "trabalho"):
        return bool(COMMS.search(t))
    if kind == "cultural":
        return bool(COMMS.search(t) or re.search(r"economia criativa|edital de circulacao|intercambio cultural", t))
    if kind in ("agropolos", "editais"):
        return bool(SERVICES.search(t) or COMMS.search(t))
    return bool(COMMS.search(t))

def category(title, source):
    t = normalize(title)
    if source.get("kind") == "agropolos" and re.search(r"processo seletiv|selecao.*profissional", t):
        return "seletivos"
    return source.get("category_hint", "servicos")

def event_type(title):
    t = normalize(title)
    for word, label in (
        ("retific", "Retificação"), ("prorrog", "Prorrogação"),
        ("credenc", "Credenciamento"), ("processo seletiv", "Processo seletivo"),
        ("mestrad", "Mestrado"), ("pregao", "Pregão"),
        ("resultado", "Resultado"), ("edital", "Edital"),
    ):
        if word in t:
            return label
    return "Publicação"

def source_link_ok(source, link):
    parsed = urlparse(link)
    original = urlparse(source["url"])
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    approved = set(source.get("allowed_domains", [original.hostname]))
    if not any(host == domain or host.endswith("." + domain) for domain in approved):
        return False
    if EXCLUDE_EXT.search(parsed.path):
        return False
    if link.rstrip("/") == source["url"].rstrip("/"):
        return False
    if source["id"] == "agropolos":
        return bool(re.search(r"/editais/[^/]+/?$", parsed.path))
    return True

def fetch_html(url):
    request = urllib.request.Request(url, headers={
        "User-Agent": "RadarDeEditais/1.1 (pesquisa de editais publicos)",
        "Accept": "text/html,application/xhtml+xml",
    })
    with urllib.request.urlopen(request, timeout=25) as response:
        if response.status >= 400:
            raise ValueError("HTTP %s" % response.status)
        content_type = response.headers.get("Content-Type", "")
        if "html" not in content_type.lower():
            raise ValueError("Resposta não é HTML: " + content_type[:90])
        body = response.read(3_000_000)
        encoding = response.headers.get_content_charset() or "utf-8"
    return body.decode(encoding, errors="replace")

def collect(source, page=None):
    if page is None:
        page = fetch_html(source["url"])
    parser = PageLinks()
    parser.feed(page)
    result = {}
    for href, label, heading in parser.links:
        link = urldefrag(urljoin(source["url"], html.unescape(href)))[0]
        if not source_link_ok(source, link):
            continue
        title = source_title(label, heading, link)
        if not relevant(title, source):
            continue
        key = link.rstrip("/")
        if key in result:
            continue
        short_hash = hashlib.sha256(key.encode()).hexdigest()[:14]
        has_comms = bool(COMMS.search(normalize(title)))
        result[key] = {
            "id": source["id"] + "-" + short_hash,
            "title": title,
            "issuer": source["name"],
            "category": category(title, source),
            "event_type": event_type(title),
            "published_at": None,
            "deadline_at": None,
            "participant": "Consultar edital oficial",
            "location": source.get("region", "Brasil"),
            "summary": (
                "Publicação localizada em uma fonte oficial. O título indica relação com comunicação ou economia criativa; confirme o objeto, requisitos e prazo."
                if has_comms else
                "Publicação localizada em uma fonte oficial. Verifique o objeto e os critérios de participação no documento completo."
            ),
            "status": "Prazo não verificado",
            "official_url": key,
            "source_id": source["id"],
            "relevance": "alta" if has_comms or source.get("kind") == "academico" else "a_verificar",
            "confirmed": ["título da publicação", "link da fonte"],
            "needs_verification": ["objeto", "requisitos", "remuneração", "prazo", "inscrições"],
            "first_seen_at": NOW,
            "last_seen_at": NOW,
        }
        if len(result) >= MAX_PER_SOURCE:
            break
    return list(result.values())

def run():
    sources = read_json(SOURCES_FILE, [])
    data = read_json(DATA_FILE, {"items": []})
    items = data.setdefault("items", [])
    if not isinstance(items, list):
        raise ValueError("Formato inválido em data/opportunities.json")
    by_url = {
        item.get("official_url", "").rstrip("/"): item
        for item in items if isinstance(item, dict) and item.get("official_url")
    }
    status = {
        "last_run_at": NOW, "overall": "ok", "sources": {}, "new_count": 0,
        "note": "A coleta identifica títulos e links; não confirma prazos, valores nem inscrições."
    }
    successes = warnings = failures = 0
    for source in sources:
        if not source.get("active"):
            continue
        try:
            found = collect(source)
            added = 0
            for item in found:
                key = item["official_url"].rstrip("/")
                if key in by_url:
                    by_url[key]["last_seen_at"] = NOW
                else:
                    items.append(item)
                    by_url[key] = item
                    added += 1
            status["new_count"] += added
            if found:
                successes += 1
                source_status = "ok"
                detail = "%d publicações reconhecidas; %d novas" % (len(found), added)
            else:
                warnings += 1
                source_status = "atencao"
                detail = "Página acessível, mas nenhum link compatível foi reconhecido; conferir estrutura"
        except Exception as exc:
            failures += 1
            source_status = "falhou"
            detail = "%s: %s" % (type(exc).__name__, str(exc)[:150])
        status["sources"][source["id"]] = {
            "state": source_status, "checked_at": NOW, "detail": detail
        }
        print(source["id"], source_status, detail, flush=True)
    if failures or warnings:
        status["overall"] = "parcial" if successes else "falhou"
    data["generated_at"] = NOW
    data["data_type"] = "coleta_automatica_parcial" if successes else "referencias_iniciais"
    data["disclaimer"] = (
        "Fontes consultadas periodicamente. Títulos e links não comprovam que uma inscrição está aberta. "
        "Confirme prazos, requisitos e valores na publicação oficial."
    )
    write_json(DATA_FILE, data)
    write_json(STATUS_FILE, status)
    print("Total:", len(items), "| novas:", status["new_count"],
          "| fontes OK:", successes, "| atenção:", warnings, "| falhas:", failures)
    # Se TODAS falharam, o workflow ainda grava o estado. Não indicar falso sucesso.
    return 0

if __name__ == "__main__":
    sys.exit(run())
