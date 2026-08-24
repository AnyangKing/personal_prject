# -*- coding: utf-8 -*-
"""수집 결과를 HTML 리포트로 만듭니다.

'추천 공고'는 키워드 점수로 자동 선별한 것이고,
'내 관심 공고'는 사용자가 별표로 직접 지정한 것입니다.
별표는 브라우저 localStorage 에 남으므로 다음날 리포트에도 그대로 따라옵니다.
"""

import html
from datetime import datetime

from . import config

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--fg:#16181d;--muted:#6b7280;--line:#e3e6ea;
      --hot:#b4231b;--hotbg:#fdf0ee;--chip:#eef1f5;--link:#1a4fd6;
      --star:#e0a800;--starbg:#fff9e6}
@media (prefers-color-scheme:dark){
  :root{--bg:#14161a;--card:#1c1f25;--fg:#e8eaed;--muted:#9aa2ad;--line:#2b3038;
        --hot:#ff8b7e;--hotbg:#2a1c1a;--chip:#282d35;--link:#8ab4ff;
        --star:#ffc93c;--starbg:#2a2413}}
*{box-sizing:border-box}
body{margin:0;padding:28px 20px 60px;background:var(--bg);color:var(--fg);
     font:15px/1.6 "Malgun Gothic","맑은 고딕",system-ui,sans-serif}
.wrap{max-width:1480px;margin:0 auto;display:grid;
      grid-template-columns:minmax(0,1fr) 340px;gap:30px;align-items:start}
h1{font-size:22px;margin:0 0 4px}
.sub{color:var(--muted);font-size:13px;margin-bottom:24px}
h2{font-size:16px;margin:32px 0 12px;padding-bottom:8px;border-bottom:2px solid var(--line)}
h2:first-of-type{margin-top:0}
.item{background:var(--card);border:1px solid var(--line);border-radius:10px;
      padding:14px 16px;margin-bottom:10px;position:relative;padding-right:52px}
.item.hot{border-color:var(--hot);background:var(--hotbg)}
.item.starred{border-color:var(--star);box-shadow:inset 3px 0 0 var(--star)}
.title{font-size:15px;font-weight:600;margin-bottom:6px}
.title a{color:var(--link);text-decoration:none}
.title a:hover{text-decoration:underline}
.meta{font-size:12.5px;color:var(--muted);display:flex;flex-wrap:wrap;gap:6px 14px}
.chip{background:var(--chip);border-radius:20px;padding:1px 9px;font-size:11.5px;color:var(--fg)}
.chip.hot{background:var(--hot);color:#fff}
.dday{font-weight:700;color:var(--hot)}
.guess{border-bottom:1px dotted var(--muted);cursor:help}
.hits{margin-top:6px;font-size:11.5px;color:var(--muted)}
.hits.body{color:var(--link)}
ul.diff{margin:8px 0 0;padding:8px 10px 8px 26px;background:var(--chip);border-radius:8px;font-size:12.5px;line-height:1.7}
ul.diff li{margin:0}
ul.diff li.more{list-style:none;margin-left:-14px;color:var(--muted)}
.note{font-size:11.5px;color:var(--muted);margin-top:4px}
.empty{color:var(--muted);padding:14px 0}
.star{position:absolute;top:10px;right:10px;width:32px;height:32px;padding:0;
      border:1px solid var(--line);border-radius:8px;background:var(--card);
      color:var(--muted);font-size:17px;line-height:1;cursor:pointer}
.star:hover{border-color:var(--star);color:var(--star)}
.star[aria-pressed="true"]{background:var(--starbg);border-color:var(--star);color:var(--star)}
aside{position:sticky;top:22px;background:var(--card);border:1px solid var(--line);
      border-radius:12px;padding:16px;max-height:calc(100vh - 44px);overflow-y:auto}
aside h2{margin:0 0 10px;font-size:15px}
.pin{border-top:1px solid var(--line);padding:10px 0 9px}
.pin:first-of-type{border-top:0}
.pin a{color:var(--link);text-decoration:none;font-size:13.5px;font-weight:600;
       display:block;margin-bottom:3px}
.pin a:hover{text-decoration:underline}
.pin .pmeta{font-size:11.5px;color:var(--muted);display:flex;gap:8px;
            justify-content:space-between;align-items:center}
.pin.done{opacity:.5}
.drop{background:none;border:0;color:var(--muted);cursor:pointer;font-size:15px;
      padding:0 2px;line-height:1}
.drop:hover{color:var(--hot)}
.tools{margin-top:14px;border-top:1px solid var(--line);padding-top:10px;
       display:flex;gap:8px;flex-wrap:wrap}
.tools button{font:inherit;font-size:12px;padding:4px 10px;border:1px solid var(--line);
              border-radius:6px;background:var(--card);color:var(--muted);cursor:pointer}
.tools button:hover{border-color:var(--link);color:var(--link)}
#backup{width:100%;margin-top:9px;height:110px;font:11.5px/1.5 Consolas,monospace;
        border:1px solid var(--line);border-radius:6px;background:var(--bg);
        color:var(--fg);padding:7px;display:none}
details.past{margin-top:32px;border-top:2px solid var(--line);padding-top:14px}
details.past summary{cursor:pointer;font-size:15px;font-weight:600;list-style:revert;color:var(--muted)}
details.past summary span{font-weight:400;font-size:12.5px}
details.past[open] summary{margin-bottom:12px}
details.past .item{opacity:.72}
table.err{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:8px}
table.err td{border-top:1px solid var(--line);padding:6px 8px;color:var(--muted)}
table.warn td{color:var(--hot)}
table.warn td:first-child{font-weight:600;white-space:nowrap}
@media(max-width:1100px){
  .wrap{grid-template-columns:1fr}
  aside{position:static;order:-1;max-height:none}
}
"""

JS = r"""
const KEY = 'rfpStarred';

function read(){
  try { return JSON.parse(localStorage.getItem(KEY)) || {}; }
  catch(e){ return {}; }
}
function write(o){ localStorage.setItem(KEY, JSON.stringify(o)); }

function dday(d){
  if(!d) return '';
  const end = new Date(d + 'T00:00:00'), now = new Date();
  now.setHours(0, 0, 0, 0);
  const n = Math.round((end - now) / 86400000);
  if(n < 0) return '마감';
  return n === 0 ? '오늘 마감' : 'D-' + n;
}

function esc(s){
  return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
  });
}

function paint(){
  const store = read();

  // 이 리포트에 떠 있는 항목의 별표 상태를 맞춥니다
  document.querySelectorAll('.star').forEach(function(b){
    const on = !!store[b.dataset.key];
    b.setAttribute('aria-pressed', on);
    b.textContent = on ? '★' : '☆';
    b.title = on ? '관심 공고에서 빼기' : '관심 공고로 지정';
    b.closest('.item').classList.toggle('starred', on);
  });

  // 오른쪽 패널: 마감이 가까운 것부터, 마감된 것은 맨 뒤로
  const list = Object.keys(store).map(function(k){
    return Object.assign({k: k}, store[k]);
  });
  list.sort(function(a, b){
    const ea = dday(a.d) === '마감', eb = dday(b.d) === '마감';
    if(ea !== eb) return ea ? 1 : -1;
    if(a.d && b.d) return a.d < b.d ? -1 : 1;
    if(!a.d !== !b.d) return a.d ? -1 : 1;
    return (b.at || '') < (a.at || '') ? -1 : 1;
  });

  document.getElementById('pinCount').textContent = list.length;
  const box = document.getElementById('pins');
  if(!list.length){
    box.innerHTML = "<div class='empty' style='font-size:13px'>"
      + "공고 오른쪽의 ☆ 를 누르면 여기에 모입니다.</div>";
    return;
  }
  box.innerHTML = list.map(function(x){
    const dd = dday(x.d);
    const when = x.d ? (dd === '마감' ? '마감됨' : '마감 ' + x.d + ' · ' + dd)
                     : '마감일 없음';
    return "<div class='pin" + (dd === '마감' ? ' done' : '') + "'>"
      + "<a href='" + esc(x.u) + "' target='_blank' rel='noopener'>" + esc(x.t) + "</a>"
      + "<div class='pmeta'><span>" + esc(x.s) + " · " + when + "</span>"
      + "<button class='drop' data-drop='" + esc(x.k) + "' title='빼기'>✕</button>"
      + "</div></div>";
  }).join('');
}

document.addEventListener('click', function(e){
  const star = e.target.closest('.star');
  if(star){
    const store = read(), k = star.dataset.key;
    if(store[k]){
      delete store[k];
    } else {
      store[k] = {t: star.dataset.title, u: star.dataset.url, s: star.dataset.site,
                  d: star.dataset.deadline, sc: star.dataset.score,
                  at: new Date().toISOString().slice(0, 10)};
    }
    write(store); paint();
    return;
  }
  const drop = e.target.closest('[data-drop]');
  if(drop){
    const store = read();
    delete store[drop.dataset.drop];
    write(store); paint();
  }
});

document.getElementById('btnBackup').onclick = function(){
  const t = document.getElementById('backup');
  const showing = t.style.display === 'block';
  t.style.display = showing ? 'none' : 'block';
  if(!showing) t.value = JSON.stringify(read(), null, 1);
};
document.getElementById('btnRestore').onclick = function(){
  const t = document.getElementById('backup');
  if(t.style.display !== 'block'){
    t.style.display = 'block';
    t.value = JSON.stringify(read(), null, 1);
    return;
  }
  try {
    const parsed = JSON.parse(t.value);
    if(typeof parsed !== 'object' || parsed === null) throw new Error('bad');
    write(parsed); paint();
    alert('불러왔습니다.');
  } catch(err){
    alert('JSON 형식이 아닙니다.');
  }
};

paint();
"""


def esc(text):
    return html.escape(str(text or ""), quote=True)


def _dday(deadline):
    if not deadline:
        return ""
    try:
        end = datetime.strptime(deadline, "%Y-%m-%d")
    except ValueError:
        return ""
    days = (end.date() - datetime.now().date()).days
    if days < 0:
        return "마감"
    if days == 0:
        return "오늘 마감"
    return f"D-{days}"


def _item_html(item):
    hot = item.get("score", 0) >= config.TOAST_MIN_SCORE
    dday = _dday(item.get("deadline"))
    key = f"{item['site']}:{item['id']}"

    meta = [f'<span class="chip{" hot" if hot else ""}">{esc(item["site_name"])}</span>']
    if item.get("org") and item["org"] != item["site_name"]:
        meta.append(f'<span>{esc(item["org"])}</span>')
    if item.get("posted"):
        meta.append(f'공고일 {esc(item["posted"])}')
    if item.get("deadline"):
        d = f'마감 {esc(item["deadline"])}'
        if dday:
            d += f' <span class="dday">{esc(dday)}</span>'
        meta.append(d)
    elif item.get("event_date"):
        e = _dday(item["event_date"])
        d = (f'<span class="guess" title="{esc(item.get("event_why", ""))}">'
             f'행사일 {esc(item["event_date"])}')
        if e:
            d += f' <span class="dday">{esc(e)}</span>'
        meta.append(d + "</span>")
    elif item.get("deadline_guess"):
        # 첨부 공고문에서 읽어낸 추정값입니다. 마감 필터에는 쓰지 않습니다.
        g = _dday(item["deadline_guess"])
        d = (f'<span class="guess" title="{esc(item.get("deadline_why", ""))}">'
             f'마감(추정) {esc(item["deadline_guess"])}')
        if g:
            d += f' <span class="dday">{esc(g)}</span>'
        meta.append(d + "</span>")
    meta.append(f'관심도 {item.get("score", 0)}점')

    hits = ""
    if item.get("hits"):
        hits = f'<div class="hits">걸린 키워드: {esc(", ".join(item["hits"][:10]))}</div>'
    if item.get("body_hits"):
        hits += (f'<div class="hits body">첨부 공고문에서: '
                 f'{esc(", ".join(item["body_hits"][:10]))}</div>')

    if item.get("changed"):
        rows = "".join(f"<li>{esc(c[:110])}</li>" for c in item["changed"])
        more = ""
        if item.get("changed_total", 0) > len(item["changed"]):
            more = (f"<li class='more'>… 외 "
                    f"{item['changed_total'] - len(item['changed'])}줄</li>")
        hits += f"<ul class='diff'>{rows}{more}</ul>"

    notes = []
    if item.get("list_only"):
        notes.append('※ 이 사이트는 직접 링크가 막혀 있어 목록으로 연결됩니다. 제목으로 찾아 주세요.')
    if item.get("detail_failed"):
        notes.append('※ 첨부 공고문을 읽지 못했습니다 — 세부 과제는 직접 열어 확인해 주세요. '
                     + (item.get("detail_note") or ""))
    note = "".join(f'<div class="note">{esc(n)}</div>' for n in notes)

    star = (f'<button class="star" data-key="{esc(key)}" data-title="{esc(item["title"])}" '
            f'data-url="{esc(item["url"])}" data-site="{esc(item["site_name"])}" '
            f'data-deadline="{esc(item.get("deadline") or item.get("deadline_guess", ""))}" '
            f'data-score="{esc(item.get("score", 0))}">&#9734;</button>')

    return (
        f'<div class="item{" hot" if hot else ""}">{star}'
        f'<div class="title"><a href="{esc(item["url"])}" target="_blank" '
        f'rel="noopener">{esc(item["title"])}</a></div>'
        f'<div class="meta">{"".join(f"<span>{m}</span>" for m in meta)}</div>'
        f"{hits}{note}</div>"
    )


def build(new_items, stats, errors, warnings=None):
    now = datetime.now()
    # 추정 마감일로 '지난 것 같다'고 본 공고는 버리지 않고 맨 아래로 내립니다.
    # 추정이 틀릴 수 있어서, 안 보이게 하되 사라지지는 않게 합니다.
    past = [i for i in new_items if i.get("expired_guess")]
    current = [i for i in new_items if not i.get("expired_guess")]

    hot = [i for i in current if i.get("score", 0) >= config.TOAST_MIN_SCORE]
    low = [i for i in current if i.get("score", 0) < config.TOAST_MIN_SCORE]
    # 첨부를 읽지 못한 공모형 공고는 점수를 믿을 수 없으므로 따로 올립니다
    check = [i for i in low if i.get("detail_failed")]
    rest = [i for i in low if not i.get("detail_failed")]

    main = [
        f"<h1>공고 리포트 · {now:%Y년 %m월 %d일}</h1>",
        f"<div class='sub'>{now:%H:%M} 수집 · 사이트 {stats['sites_ok']}/{stats['sites_total']}개 성공 · "
        f"전체 {stats['total']}건 중 신규 {stats.get('fresh', len(new_items))}건 · "
        f"이 리포트에 표시 {len(current)}건 (추천 {len(hot)}건)</div>",
        f"<h2>추천 공고 {len(hot)}건 <span style='font-weight:400;color:var(--muted);"
        f"font-size:13px'>(키워드 관심도 {config.TOAST_MIN_SCORE}점 이상)</span></h2>",
    ]
    main.append("".join(_item_html(i) for i in hot) if hot
                else "<div class='empty'>오늘은 키워드에 걸린 신규 공고가 없습니다.</div>")

    if check:
        main.append(
            f"<h2>직접 확인 필요 {len(check)}건 <span style='font-weight:400;"
            f"color:var(--muted);font-size:13px'>(첨부 공고문을 읽지 못해 "
            f"점수를 믿을 수 없습니다)</span></h2>")
        main.append("".join(_item_html(i) for i in check))

    main.append(f"<h2>그 밖의 신규 공고 {len(rest)}건</h2>")
    main.append("".join(_item_html(i) for i in rest) if rest
                else "<div class='empty'>없습니다.</div>")

    if warnings:
        main.append(
            f"<h2>점검 필요 {len(warnings)}곳 <span style='font-weight:400;color:var(--muted);"
            f"font-size:13px'>(수집은 됐지만 건수가 평소와 다릅니다)</span></h2>"
            "<table class='err warn'>")
        for site, msg in warnings:
            main.append(f"<tr><td>{esc(site)}</td><td>{esc(msg[:200])}</td></tr>")
        main.append("</table>")

    if past:
        past.sort(key=lambda i: -(i.get("score") or 0))
        main.append(
            "<details class='past'><summary>마감된 것으로 보이는 공고 "
            f"{len(past)}건 <span>— 첨부 공고문에서 읽은 추정 마감일 기준입니다. "
            "잘못 판정됐을 수 있어 지우지 않고 접어 둡니다.</span></summary>")
        main.append("".join(_item_html(i) for i in past))
        main.append("</details>")

    if errors:
        main.append(f"<h2>수집 실패 {len(errors)}건</h2><table class='err'>")
        for site, msg in errors:
            main.append(f"<tr><td>{esc(site)}</td><td>{esc(msg[:200])}</td></tr>")
        main.append("</table>")

    aside = (
        "<aside><h2>내 관심 공고 <span id='pinCount'>0</span>건</h2>"
        "<div id='pins'></div>"
        "<div class='tools'>"
        "<button id='btnBackup'>백업 보기</button>"
        "<button id='btnRestore'>붙여넣어 복원</button></div>"
        "<textarea id='backup' spellcheck='false'></textarea>"
        "<div class='note' style='margin-top:8px'>별표는 이 브라우저에 저장되어 "
        "다음날 리포트에도 그대로 남습니다. 다른 브라우저로 옮길 때는 백업을 쓰세요.</div>"
        "</aside>"
    )

    doc = (
        "<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>공고 리포트 {now:%Y-%m-%d}</title><style>{CSS}</style></head><body>"
        f"<div class='wrap'><main>{''.join(main)}</main>{aside}</div>"
        f"<script>{JS}</script></body></html>"
    )

    config.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = config.REPORT_DIR / f"{now:%Y-%m-%d}.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    return path
