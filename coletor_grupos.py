# -*- coding: utf-8 -*-
"""
Coletor de links de grupos de WhatsApp
--------------------------------------
Varre sites publicos de divulgacao de grupos, extrai os links de convite
(chat.whatsapp.com/...), remove repetidos, ignora os que voce ja coletou em
rodadas anteriores e gera um painel HTML com botao de copiar.

Rode com EXECUTAR.bat (ou: python coletor_grupos.py)
"""

import json
import os
import re
import sys
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

try:
    import requests
except ImportError:
    print("Falta a biblioteca 'requests'. Rode:  pip install requests")
    sys.exit(1)


# ============================================================
# CONFIGURACAO  (mexa so aqui)
# ============================================================

# Quantos grupos buscar por categoria, em cada site
LIMITE_POR_CATEGORIA = 120

# So aceita grupos publicados nos ultimos N dias (link novo = mais chance de estar vivo)
DIAS_MAXIMOS = 150

# Quantas requisicoes ao mesmo tempo (nao passe muito disso para nao tomar bloqueio)
PARALELO = 6

# Conferir se a pagina do convite responde antes de salvar
CHECAR_LINKS = True

# Categorias ligadas. Coloque False para desligar alguma.
CATEGORIAS_ATIVAS = {
    "Figurinhas": True,
    "Namoro": True,
    "Amizade e conversa": True,
    "Memes e humor": True,
}

# Mapa: categoria -> lista de (site, id da categoria no site)
FONTES = {
    "Figurinhas": [
        ("linkdegrupo.com.br", 41),
        ("grupodewhats.app", 9),
    ],
    "Namoro": [
        ("linkdegrupo.com.br", 69),
        ("linkdegrupo.com.br", 7),
        ("grupodewhats.app", 4),
    ],
    "Amizade e conversa": [
        ("linkdegrupo.com.br", 6),
        ("grupodewhats.app", 1),
    ],
    "Memes e humor": [
        ("linkdegrupo.com.br", 46),
    ],
}

PASTA = os.path.dirname(os.path.abspath(__file__))
ARQ_HISTORICO = os.path.join(PASTA, "historico.json")
ARQ_PAINEL = os.path.join(PASTA, "painel.html")
ARQ_CSV = os.path.join(PASTA, "grupos.csv")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

SESSAO = requests.Session()
SESSAO.headers.update({
    "User-Agent": UA,
    "Accept-Language": "pt-BR,pt;q=0.9",
})

RE_CONVITE = re.compile(r"chat\.whatsapp\.com/(?:invite/)?([A-Za-z0-9_-]{15,30})")


# ============================================================
# FUNCOES
# ============================================================

def carregar_historico():
    if os.path.exists(ARQ_HISTORICO):
        try:
            with open(ARQ_HISTORICO, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def salvar_historico(codigos):
    with open(ARQ_HISTORICO, "w", encoding="utf-8") as f:
        json.dump(sorted(codigos), f, ensure_ascii=False, indent=0)


def limpar_titulo(t):
    t = re.sub(r"<[^>]+>", "", t or "")
    subs = {"&#8211;": "-", "&#038;": "&", "&amp;": "&", "&#8217;": "'",
            "&quot;": '"', "&#8220;": '"', "&#8221;": '"', "&nbsp;": " ",
            "&#39;": "'", "&lt;": "<", "&gt;": ">"}
    for k, v in subs.items():
        t = t.replace(k, v)
    return re.sub(r"\s+", " ", t).strip()


def listar_posts(site, cat_id, limite, data_corte):
    """Usa a API publica do WordPress para listar os posts mais novos da categoria."""
    posts, pagina = [], 1
    while len(posts) < limite:
        url = (f"https://{site}/wp-json/wp/v2/posts"
               f"?categories={cat_id}&per_page=100&page={pagina}"
               f"&orderby=date&order=desc&_fields=link,title,date")
        try:
            r = SESSAO.get(url, timeout=25)
        except Exception as e:
            print(f"   ! erro de conexao em {site}: {e}")
            break
        if r.status_code == 400:      # acabou a paginacao
            break
        if r.status_code != 200:
            print(f"   ! {site} respondeu {r.status_code} (categoria {cat_id})")
            break
        try:
            lote = r.json()
        except Exception:
            break
        if not lote:
            break
        parou = False
        for p in lote:
            data = (p.get("date") or "")[:10]
            if data and data < data_corte:
                parou = True
                break
            posts.append({
                "site": site,
                "url": p.get("link", ""),
                "titulo": limpar_titulo((p.get("title") or {}).get("rendered", "")),
                "data": data,
            })
        if parou or len(lote) < 100:
            break
        pagina += 1
        time.sleep(0.3)
    return posts[:limite]


def extrair_convite(post):
    """Abre a pagina do grupo e pega o link de convite."""
    try:
        r = SESSAO.get(post["url"], timeout=25)
        if r.status_code != 200:
            return None
        m = RE_CONVITE.search(r.text)
        if not m:
            return None
        codigo = m.group(1)
        return {
            "codigo": codigo,
            "link": f"https://chat.whatsapp.com/{codigo}",
            "titulo": post["titulo"] or "(sem nome)",
            "data": post["data"],
            "site": post["site"],
            "categoria": post["categoria"],
        }
    except Exception:
        return None


def checar_status_http(item):
    """Confere se a pagina do convite responde 200. Nao garante que o grupo
    esta aberto (o WhatsApp so revela isso ao abrir no celular), mas descarta
    codigo quebrado / fora do ar."""
    try:
        r = SESSAO.head(item["link"], timeout=20, allow_redirects=True)
        if r.status_code >= 400:
            r = SESSAO.get(item["link"], timeout=20, allow_redirects=True)
        item["http"] = r.status_code
    except Exception:
        item["http"] = 0
    return item


# ============================================================
# PAINEL HTML
# ============================================================

PAGINA = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Links de grupos - coleta de __DATA__</title>
<style>
:root{--bg:#0f1720;--card:#18232f;--line:#26364a;--txt:#e8eef5;--dim:#93a4b8;--ok:#25d366;--okd:#128c4a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
header{position:sticky;top:0;z-index:5;background:#101b26;border-bottom:1px solid var(--line);padding:14px 18px}
h1{margin:0 0 4px;font-size:18px}
.sub{color:var(--dim);font-size:13px}
.barra{display:flex;flex-wrap:wrap;gap:8px;margin-top:12px;align-items:center}
button{cursor:pointer;border:0;border-radius:9px;padding:9px 14px;font-size:14px;font-weight:600;background:var(--ok);color:#04220f}
button:hover{background:var(--okd);color:#fff}
button.sec{background:#25384c;color:var(--txt)}
button.sec:hover{background:#31485f}
input[type=search]{flex:1;min-width:180px;background:#0b141c;border:1px solid var(--line);color:var(--txt);border-radius:9px;padding:9px 12px;font-size:14px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.chip{border:1px solid var(--line);background:#0b141c;color:var(--dim);border-radius:20px;padding:5px 12px;font-size:13px;cursor:pointer;user-select:none}
.chip.on{background:var(--ok);color:#04220f;border-color:var(--ok);font-weight:700}
main{padding:14px 18px 60px;max-width:1100px;margin:0 auto}
.item{display:flex;gap:10px;align-items:flex-start;background:var(--card);border:1px solid var(--line);border-radius:11px;padding:11px 13px;margin-bottom:8px}
.item.usado{opacity:.42}
.item input{margin-top:3px;width:17px;height:17px;accent-color:var(--ok);flex:none}
.info{min-width:0;flex:1}
.nome{font-weight:600;word-break:break-word}
.meta{color:var(--dim);font-size:12px;margin-top:3px}
.meta a{color:#63b3ed;text-decoration:none}
.acoes{display:flex;gap:6px;flex:none}
.mini{font-size:12px;padding:6px 9px;border-radius:7px;background:#25384c;color:var(--txt)}
.tag{display:inline-block;background:#20303f;border-radius:5px;padding:1px 7px;margin-right:6px;font-size:11px}
#aviso{position:fixed;left:50%;bottom:24px;transform:translateX(-50%) translateY(80px);background:var(--ok);color:#04220f;
padding:11px 20px;border-radius:10px;font-weight:700;transition:.25s;pointer-events:none}
#aviso.ver{transform:translateX(-50%) translateY(0)}
.vazio{color:var(--dim);padding:30px 0;text-align:center}
</style></head><body>
<header>
  <h1>Links de grupos &middot; __TOTAL__ encontrados</h1>
  <div class="sub">Coleta de __DATA__ &middot; ja tirando os repetidos e os que voce coletou antes</div>
  <div class="chips" id="chips"></div>
  <div class="barra">
    <input type="search" id="busca" placeholder="filtrar pelo nome do grupo...">
    <button onclick="copiar(true)">Copiar selecionados</button>
    <button class="sec" onclick="copiar(false)">Copiar todos da tela</button>
    <button class="sec" onclick="marcar(true)">Marcar todos</button>
    <button class="sec" onclick="marcar(false)">Desmarcar</button>
    <button class="sec" onclick="limparUsados()">Limpar &quot;ja entrei&quot;</button>
  </div>
</header>
<main id="lista"></main>
<div id="aviso">copiado!</div>
<script>
const DADOS = __DADOS__;
let cats = [...new Set(DADOS.map(d=>d.categoria))];
let ativas = new Set(cats);
let usados = new Set();
try{ usados = new Set(JSON.parse(localStorage.getItem('grp_usados')||'[]')); }catch(e){}
function salvarUsados(){ try{ localStorage.setItem('grp_usados', JSON.stringify([...usados])); }catch(e){} }

const elChips = document.getElementById('chips');
cats.forEach(c=>{
  const b=document.createElement('div'); b.className='chip on'; b.textContent=c+' ('+DADOS.filter(d=>d.categoria===c).length+')';
  b.onclick=()=>{ if(ativas.has(c)){ativas.delete(c);b.classList.remove('on');} else {ativas.add(c);b.classList.add('on');} render(); };
  elChips.appendChild(b);
});

function visiveis(){
  const q=document.getElementById('busca').value.toLowerCase().trim();
  return DADOS.filter(d=>ativas.has(d.categoria) && (!q || d.titulo.toLowerCase().includes(q)));
}
function render(){
  const alvo=document.getElementById('lista'); const itens=visiveis();
  if(!itens.length){ alvo.innerHTML='<div class="vazio">nada aqui com esse filtro</div>'; return; }
  alvo.innerHTML = itens.map(d=>`
    <div class="item ${usados.has(d.codigo)?'usado':''}">
      <input type="checkbox" data-cod="${d.codigo}">
      <div class="info">
        <div class="nome">${esc(d.titulo)}</div>
        <div class="meta"><span class="tag">${esc(d.categoria)}</span>${d.data||''} &middot; <a href="${d.link}" target="_blank" rel="noopener">${d.link}</a></div>
      </div>
      <div class="acoes">
        <button class="mini" onclick="copiarUm('${d.codigo}')">copiar</button>
        <button class="mini" onclick="toggleUsado('${d.codigo}')">ja entrei</button>
      </div>
    </div>`).join('');
}
function esc(s){ return String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function marcar(v){ document.querySelectorAll('#lista input[type=checkbox]').forEach(c=>c.checked=v); }
function toggleUsado(cod){ usados.has(cod)?usados.delete(cod):usados.add(cod); salvarUsados(); render(); }
function limparUsados(){ usados=new Set(); salvarUsados(); render(); }

function formatar(itens){
  return itens.map((d,i)=>`${i+1} - Nome do grupo: ${d.titulo}\\nlink: ${d.link}`).join('\\n\\n');
}
function copiarUm(cod){ const d=DADOS.find(x=>x.codigo===cod); paraArea(formatar([d])); }
function copiar(soSelecionados){
  let itens=visiveis();
  if(soSelecionados){
    const marcados=new Set([...document.querySelectorAll('#lista input:checked')].map(c=>c.dataset.cod));
    itens=itens.filter(d=>marcados.has(d.codigo));
    if(!itens.length){ aviso('nenhum marcado'); return; }
  }
  paraArea(formatar(itens), itens.length+' copiados!');
}
function paraArea(txt, msg){
  const ta=document.createElement('textarea'); ta.value=txt;
  ta.style.position='fixed'; ta.style.opacity='0'; document.body.appendChild(ta);
  ta.select();
  let ok=false; try{ ok=document.execCommand('copy'); }catch(e){}
  document.body.removeChild(ta);
  if(!ok && navigator.clipboard){ navigator.clipboard.writeText(txt); ok=true; }
  aviso(ok ? (msg||'copiado!') : 'nao consegui copiar');
}
let t; function aviso(m){ const a=document.getElementById('aviso'); a.textContent=m; a.classList.add('ver'); clearTimeout(t); t=setTimeout(()=>a.classList.remove('ver'),1600); }
document.getElementById('busca').addEventListener('input', render);
render();
</script></body></html>"""


def gerar_painel(itens):
    html = (PAGINA
            .replace("__DADOS__", json.dumps(itens, ensure_ascii=False))
            .replace("__TOTAL__", str(len(itens)))
            .replace("__DATA__", datetime.now().strftime("%d/%m/%Y %H:%M")))
    with open(ARQ_PAINEL, "w", encoding="utf-8") as f:
        f.write(html)


def gerar_csv(itens):
    import csv
    with open(ARQ_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["categoria", "nome do grupo", "link", "data", "site"])
        for d in itens:
            w.writerow([d["categoria"], d["titulo"], d["link"], d["data"], d["site"]])


# ============================================================
# PRINCIPAL
# ============================================================

def main():
    print("=" * 58)
    print("  COLETOR DE LINKS DE GRUPOS DE WHATSAPP")
    print("=" * 58)

    historico = carregar_historico()
    print(f"\n{len(historico)} links ja coletados em rodadas anteriores (serao ignorados)\n")

    corte = (datetime.now() - timedelta(days=DIAS_MAXIMOS)).strftime("%Y-%m-%d")
    posts = []

    for categoria, ligada in CATEGORIAS_ATIVAS.items():
        if not ligada or categoria not in FONTES:
            continue
        print(f"[{categoria}]")
        for site, cat_id in FONTES[categoria]:
            achados = listar_posts(site, cat_id, LIMITE_POR_CATEGORIA, corte)
            for p in achados:
                p["categoria"] = categoria
            posts.extend(achados)
            print(f"   {site}: {len(achados)} paginas de grupo")

    if not posts:
        print("\nNao veio nada. Confira sua internet ou tente de novo mais tarde.")
        return

    print(f"\nAbrindo {len(posts)} paginas para pegar os links...")
    itens, vistos = [], set(historico)
    feitos = 0
    with ThreadPoolExecutor(max_workers=PARALELO) as ex:
        for res in ex.map(extrair_convite, posts):
            feitos += 1
            if feitos % 25 == 0:
                print(f"   {feitos}/{len(posts)}")
            if res and res["codigo"] not in vistos:
                vistos.add(res["codigo"])
                itens.append(res)

    print(f"\n{len(itens)} links novos (sem repetidos e sem os das rodadas anteriores)")

    if itens and CHECAR_LINKS:
        print("Conferindo se as paginas de convite respondem...")
        with ThreadPoolExecutor(max_workers=PARALELO) as ex:
            itens = list(ex.map(checar_status_http, itens))
        antes = len(itens)
        itens = [d for d in itens if d.get("http") == 200]
        print(f"   {antes - len(itens)} descartados por nao responderem")

    itens.sort(key=lambda d: d["data"], reverse=True)
    itens.sort(key=lambda d: d["categoria"])

    gerar_painel(itens)
    gerar_csv(itens)
    salvar_historico(vistos)

    print("\n" + "=" * 58)
    print(f"  PRONTO: {len(itens)} links no painel")
    print(f"  {ARQ_PAINEL}")
    print(f"  {ARQ_CSV}")
    print("=" * 58)

    try:
        webbrowser.open("file:///" + ARQ_PAINEL.replace("\\", "/"))
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ncancelado.")
    input("\nAperte ENTER para fechar...")
