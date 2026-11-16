#!/usr/bin/env python3
"""Verificação conservadora de links públicos. Não determina elegibilidade ou prazos."""
import hashlib, html, json, re, sys, urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/opportunities.json"
STATUS = ROOT / "data/monitor_status.json"
SOURCES = ROOT / "config/sources.json"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")
TERMS = re.compile(r"edital|credenciamento|processo seletivo|seleção|mestrado|inscriç|retificaç|prorrogaç|aditivo", re.I)
STOP = re.compile(r"login|contato|sobre|pesquisa|galeria|menu", re.I)

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links=[]; self.href=None; self.parts=[]
    def handle_starttag(self, tag, attrs):
        if tag=="a":
            self.href=dict(attrs).get("href"); self.parts=[]
    def handle_data(self, data):
        if self.href is not None: self.parts.append(data)
    def handle_endtag(self, tag):
        if tag=="a" and self.href is not None:
            self.links.append((self.href, " ".join("".join(self.parts).split())))
            self.href=None; self.parts=[]

def load(path, fallback):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError): return fallback

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

def collect(src):
    request=urllib.request.Request(src["url"],headers={"User-Agent":"RadarDeEditais/1.0 (monitor publico)","Accept":"text/html"})
    with urllib.request.urlopen(request, timeout=25) as response:
        raw=response.read(3_000_000)
        encoding=response.headers.get_content_charset() or "utf-8"
    parser=Links()
    parser.feed(raw.decode(encoding,errors="replace"))
    result={}
    base=urlparse(src["url"])
    for href,label in parser.links:
        link=urldefrag(urljoin(src["url"],html.unescape(href)))[0]
        url=urlparse(link)
        if url.scheme not in ("http","https") or url.hostname != base.hostname: continue
        if link.rstrip("/") == src["url"].rstrip("/"): continue
        if src["id"]=="agropolos" and not re.search(r"/editais/[^/]{8,}/?$",url.path): continue
        if src["id"]=="ppgcom" and not re.search(r"/pt/[^/]{8,}/?$",url.path): continue
        if not (14<=len(label)<=220 and TERMS.search(label) and not STOP.search(label)):continue
        key=hashlib.sha256(link.encode()).hexdigest()[:14]
        result[link]={
          "id":src["id"]+"-"+key,"title":label,"issuer":src["name"],
          "category":src["category_hint"],"event_type":"Publicação",
          "published_at":None,"deadline_at":None,"participant":"Verificar edital",
          "location":"Ceará" if src["id"]=="agropolos" else "Fortaleza, CE",
          "summary":"Publicação encontrada em página oficial. Confira requisitos e prazos no documento completo.",
          "status":"Prazo não verificado","official_url":link,"source_id":src["id"],
          "confirmed":["título","link oficial"],"needs_verification":["objeto","requisitos","valor","prazo"],
          "first_seen_at":NOW,"last_seen_at":NOW}
    if not result: raise ValueError("Nenhuma publicação reconhecida; estrutura da página pode ter mudado")
    return list(result.values())

def main():
    data=load(DATA,{"items":[]})
    status={"last_run_at":NOW,"sources":{},"note":"A coleta pode falhar por indisponibilidade ou mudança das páginas"}
    existing=data.setdefault("items",[])
    by_url={x.get("official_url","").rstrip("/"):x for x in existing}
    added=0
    for source in load(SOURCES,[]):
        if not source.get("active"): continue
        try:
            found=collect(source)
            count=0
            for item in found:
                key=item["official_url"].rstrip("/")
                if key in by_url: by_url[key]["last_seen_at"]=NOW
                else:
                    existing.append(item); by_url[key]=item; count+=1
            added+=count
            status["sources"][source["id"]]={"state":"ok","checked_at":NOW,"detail":f"{len(found)} links reconhecidos; {count} novos"}
            print(source["id"],"OK",len(found),"links",count,"novos")
        except Exception as err:
            status["sources"][source["id"]]={"state":"falhou","checked_at":NOW,"detail":str(err)[:160]}
            print(source["id"],"FALHOU",err,file=sys.stderr)
    data["generated_at"]=NOW
    data["data_type"]="coleta_automatica_parcial" if any(x["state"]=="ok" for x in status["sources"].values()) else "referencias_iniciais"
    data["disclaimer"]="A coleta identifica links, mas não verifica prazos, documentos ou elegibilidade."
    status["note"]=f"{added} novas publicações identificadas; confirme os requisitos na fonte."
    write(DATA,data); write(STATUS,status)

if __name__=="__main__":main()
