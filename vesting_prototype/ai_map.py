"""Interactive mind map for the 'How I used AI' section.

A self-contained HTML/JS panel shown with streamlit.components.v1.html. It takes plain data (steps, judgment calls,
limits, research map, pre-rendered output tables) and draws a hub with expandable branches. Click a branch to expand
it, click a step to open its detail, use Tour to walk through everything in order. Imports nothing from the engine.
"""
from __future__ import annotations

import json

HEIGHT = 532

SHORT = ["Frame and write the PRD", "Learn the domain", "Close open questions", "AI as a tutor", "Synthetic data",
         "Build, test, host", "Pre-lapse and leave", "UI review", "Employee drill-down", "Real equity programs"]

# branch id, title, subtitle, emoji, side, children: ("step", n) | ("judg",) | ("limits",)
BRANCHES = [
    ("frame", "Frame the problem", "Goal, scope, PRD", "\U0001F9ED", "L", [("step", 1)]),
    ("learn", "Learn the domain", "Research and assumptions", "\U0001F4DA", "L", [("step", 2), ("step", 3), ("step", 4)]),
    ("data", "Build the data", "Synthetic, global", "\U0001F4CA", "L", [("step", 5)]),
    ("build", "Build and host", "Prototype to a link", "\U0001F6E0", "L", [("step", 6)]),
    ("ops", "Real operations", "Leave, pre-lapse", "\U0001F50E", "R", [("step", 7)]),
    ("ux", "Make it usable", "Phone and desktop", "\U0001F3A8", "R", [("step", 8), ("step", 9)]),
    ("model", "Go deeper", "Award types, rules, what-if", "⚙️", "R", [("step", 10)]),
    ("me", "Calls & limits", "Decisions, caveats", "⚖️", "R", [("judg",), ("limits",)]),
]

PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{--g:#0fa97f;--gd:#0b4a3c;--mint:#e6fbf4;--ink:#0b2b24;--amb:#f59e0b;--blue:#2563eb}
*{box-sizing:border-box}
html,body{margin:0;height:100%;font-family:"Segoe UI",system-ui,-apple-system,Roboto,sans-serif;color:var(--ink);background:transparent}
.root{position:relative;height:100%;min-height:560px;border-radius:18px;overflow:clip;background:var(--mint);display:flex;flex-direction:column}
.ban{background:var(--g);color:var(--gd);padding:8px 16px;display:flex;gap:14px;align-items:center;justify-content:space-between;flex-wrap:wrap}
.ban h1{margin:0;font:700 22px/1.1 Georgia,"Times New Roman",serif;letter-spacing:-.01em}
.ban p{display:none}
.tools{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.btn{border:0;border-radius:999px;padding:6px 12px;font-weight:600;font-size:12px;cursor:pointer;background:var(--gd);color:#e6fbf4;
     transition:transform .15s,box-shadow .15s}
.btn:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(0,0,0,.25)}
.btn.alt{background:rgba(255,255,255,.35);color:var(--gd)}
.chip{font-size:11px;font-weight:700;background:rgba(255,255,255,.45);border-radius:999px;padding:5px 10px}
.stage{position:relative;flex:1;min-height:0;overflow:hidden}
.sc{position:absolute;left:0;top:0;width:1100px;transform-origin:0 0}
.nodes{position:absolute;inset:0;z-index:2}
.hubw{position:absolute;left:50%;top:14px;transform:translateX(-50%);z-index:3}
.hub{position:relative;width:128px;height:128px;border-radius:50%;background:var(--gd);color:#fff;display:flex;flex-direction:column;
     align-items:center;justify-content:center;text-align:center;padding:12px;box-shadow:0 0 0 8px var(--g),0 8px 22px rgba(11,74,60,.35)}
.hub b{font:700 16px/1.15 Georgia,serif}.hub small{display:block;margin-top:4px;font-size:10px;opacity:.8;line-height:1.25}
.hub::after{content:"";position:absolute;inset:-8px;border-radius:50%;border:2px solid var(--g);animation:pulse 3s ease-out infinite}
@keyframes pulse{0%{transform:scale(1);opacity:.7}100%{transform:scale(1.22);opacity:0}}
svg.ln{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:1}
svg.ln line{stroke:var(--gd);stroke-width:2;opacity:.55;transition:stroke .2s,stroke-width .2s,opacity .2s}
svg.ln line.on{stroke:var(--g);stroke-width:4;opacity:1}
svg.ln circle{fill:var(--gd)}
.br{position:absolute;width:0;height:0;animation:pop .5s both}
@keyframes pop{from{opacity:0;transform:scale(.8)}to{opacity:1;transform:none}}
.ico{position:absolute;left:-28px;top:-28px;width:56px;height:56px;border-radius:50%;border:0;cursor:pointer;font-size:24px;color:#fff;
     background:var(--gd);box-shadow:0 0 0 4px var(--g);transition:transform .2s,box-shadow .2s,background .2s}
.ico:hover{transform:scale(1.08)}
.br.open .ico{background:var(--g);box-shadow:0 0 0 4px var(--gd)}
.lb{position:absolute;top:-28px;width:190px}
.br.L .lb{right:40px;text-align:right}.br.R .lb{left:40px;text-align:left}
.br.B .lb{top:36px;left:-59px;width:118px;text-align:center}
.lab{border:0;background:none;cursor:pointer;color:var(--gd);text-align:inherit;padding:2px 0;width:100%}
.lab b{display:block;font:700 15px/1.15 Georgia,serif}.br.B .lab b{font-size:14px}
.lab span{display:block;font-size:10.5px;opacity:.75;margin-top:1px;line-height:1.2}
.kids{display:flex;flex-direction:column;gap:4px;max-height:0;opacity:0;overflow:hidden;transition:max-height .45s ease,opacity .35s,margin .35s}
.br.open .kids{max-height:300px;opacity:1;margin-top:5px}
.pill{border:1.5px solid var(--g);background:#fff;color:var(--gd);border-radius:12px;padding:4px 8px;font-size:11.5px;font-weight:600;
      cursor:pointer;text-align:left;line-height:1.25;width:100%;transition:background .15s,transform .15s}
.br.B .pill{font-size:11px;padding:4px 6px}
.pill:hover{background:var(--g);color:#fff;transform:scale(1.03)}
.pill.seen::after{content:" \2713";font-weight:800}
.pill.judg{border-color:var(--blue)}.pill.limit{border-color:var(--amb)}
.scrim{position:fixed;inset:0;background:rgba(6,35,28,.55);opacity:0;pointer-events:none;transition:opacity .25s;z-index:20}
.dr{position:fixed;top:0;right:0;bottom:0;width:min(640px,94%);background:#fff;z-index:21;transform:translateX(105%);
    transition:transform .35s cubic-bezier(.2,.8,.2,1);display:flex;flex-direction:column;box-shadow:-10px 0 30px rgba(0,0,0,.25)}
.root.dopen .scrim{opacity:1;pointer-events:auto}.root.dopen .dr{transform:none}
.dh{background:var(--gd);color:#fff;padding:14px 16px;display:flex;gap:12px;align-items:center}
.dn{flex:0 0 auto;width:38px;height:38px;border-radius:50%;background:var(--g);display:flex;align-items:center;justify-content:center;font-weight:800}
.dh h2{margin:0;font:700 19px/1.2 Georgia,serif;flex:1}
.x{border:0;background:rgba(255,255,255,.18);color:#fff;border-radius:50%;width:34px;height:34px;font-size:18px;cursor:pointer}
.db{flex:1;overflow:auto;padding:14px 16px}
.cols{display:grid;gap:10px}
.cc{border-radius:12px;padding:10px 12px;font-size:14px;line-height:1.4}
.cc h4{margin:0 0 5px;font-size:11px;letter-spacing:.07em;text-transform:uppercase;opacity:.7}
.cc ul{margin:0;padding-left:18px}.cc.me{background:#e8efff}.cc.ai{background:#dcf8ee}.cc.dec{background:#fdf0d4}
.cc q{font-style:italic;quotes:"\201C" "\201D"}
.out{margin-top:12px}.out h4{margin:0 0 6px;font-size:12px;text-transform:uppercase;letter-spacing:.07em;opacity:.7}
.ai-tbl{width:100%;border-collapse:collapse;font-size:12.5px}.ai-tbl th,.ai-tbl td{border:1px solid #cfd8d5;padding:5px 7px;text-align:left;vertical-align:top}
.ai-tbl th{background:#eef3f1;font-size:10.5px;text-transform:uppercase}.ai-tblwrap{overflow-x:auto}
.ai-cap{font-size:12px;opacity:.7;margin:5px 0}.ai-pill{display:inline-block;font-size:12px;border:1px solid #9bb;border-radius:999px;padding:2px 9px;margin:2px 4px 2px 0}
.rm{display:grid;grid-template-columns:1fr 1fr;gap:10px}.rm h5{margin:0 0 6px;font-size:11px;letter-spacing:.07em;text-transform:uppercase}
details.rb{border-radius:10px;margin-bottom:6px;border:1px solid;overflow:hidden}
details.rb.dn2{background:#e4f8ef;border-color:#0fa97f}details.rb.td{background:#fff4dc;border-color:#f59e0b;border-style:dashed}
details.rb summary{cursor:pointer;font-weight:700;font-size:13px;padding:7px 10px;list-style:none;display:flex;justify-content:space-between}
details.rb summary::after{content:"+";font-weight:800}details.rb[open] summary::after{content:"\2212"}
details.rb ul{margin:0;padding:2px 10px 8px 26px;font-size:12.5px}
.mini{display:flex;gap:6px;margin-bottom:8px}.mini button{border:1px solid #9bb;background:#fff;border-radius:999px;font-size:11px;padding:3px 10px;cursor:pointer}
.jc{border:1px solid #cfd8d5;border-radius:12px;padding:9px 12px;margin-bottom:8px;font-size:14px;line-height:1.4}.jc b{display:block;margin-bottom:2px}
.lm{border-left:4px solid var(--amb);background:#fff7e6;padding:8px 12px;margin-bottom:8px;border-radius:0 10px 10px 0;font-size:14px;line-height:1.4}
.df{display:flex;justify-content:space-between;gap:8px;padding:10px 14px;border-top:1px solid #e1e8e5;background:#f6faf8}
.df .btn{background:var(--gd)}.df .btn[disabled]{opacity:.35;cursor:default}.df span{align-self:center;font-size:12px;opacity:.7}
.root.m .stage{display:flex;flex-direction:column;overflow:auto;padding:10px 12px 18px}
.root.m .sc{position:static;width:auto;height:auto!important;transform:none!important;display:flex;flex-direction:column}
.root.m .hubw{position:static;transform:none;display:flex;justify-content:center;padding:6px 0 16px}
.root.m .hub{width:150px;height:150px;padding:14px}.root.m .hub b{font-size:16px}.root.m .hub small{display:none}
.root.m .nodes{position:static;display:flex;flex-direction:column;gap:12px}
.root.m svg.ln{display:none}
.root.m .br{position:relative;width:auto;height:auto;display:flex;align-items:flex-start;gap:12px;animation:none}
.root.m .ico{position:static;flex:0 0 auto;width:60px;height:60px;font-size:26px}
.root.m .lb,.root.m .br.L .lb,.root.m .br.R .lb,.root.m .br.B .lb{position:static;width:auto;flex:1;text-align:left;top:auto}
.root.m .br.B .lab b{font-size:15px}.root.m .br.B .pill{font-size:11.5px}
.root.m .br.open .kids{max-height:400px}
.root.m .hub{width:84px;height:84px;padding:6px;box-shadow:0 0 0 8px var(--g),0 6px 18px rgba(11,74,60,.3)}.root.m .hub b{font-size:11px}.root.m.t .hubw{display:none}
.root.m .hubw{padding:2px 0 10px}.root.m .nodes{gap:10px}.root.m .ico{width:46px;height:46px;font-size:21px}
.root.m .lab b{font-size:15px}.root.m .lab span{font-size:11.5px}
.root.m.t .nodes{display:grid;grid-template-columns:1fr 1fr;gap:10px 18px;align-items:start}
.root.m .ban{padding:10px 16px}.root.m .ban h1{font-size:22px}.root.m .ban p{display:none}.root.m .rm{grid-template-columns:1fr}
.root.m .dr{width:100%;top:8%;border-radius:18px 18px 0 0;transform:translateY(105%)}.root.m.dopen .dr{transform:none}
</style></head><body>
<div class="root" id="root">
 <div class="ban"><div><h1>How I used AI</h1><p>A map of the product work: tap a branch to expand it, tap a step for the detail, or take the tour.</p></div>
  <div class="tools"><span class="chip" id="prog"></span><button class="btn" id="tour">&#9654; Tour</button>
  <button class="btn alt" id="exp">Expand all</button><button class="btn alt" id="col">Collapse all</button></div></div>
 <div class="stage" id="stage"><div class="sc" id="sc"><svg class="ln" id="ln"></svg>
  <div class="hubw"><div class="hub"><b>Product work with AI</b><small>Learn, research, decide, build</small></div></div>
  <div class="nodes" id="nodes"></div></div></div>
 <div class="scrim" id="scrim"></div>
 <div class="dr" id="dr"><div class="dh"><div class="dn" id="dn"></div><h2 id="dt"></h2><button class="x" id="dx" aria-label="Close">&times;</button></div>
  <div class="db" id="db"></div>
  <div class="df"><button class="btn" id="prev">&larr; Back</button><span id="pos"></span><button class="btn" id="next">Next &rarr;</button></div></div>
</div>
<script type="application/json" id="d">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('d').textContent);
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const root=$('root');
const ALL=[];            // ordered items for the tour
D.branches.forEach(b=>b.kids.forEach(k=>ALL.push({b:b.id,k})));
const key=k=>k.t+(k.n||'');
const seen=new Set(), open=new Set();
let cur=-1;

function label(k){return k.t==='step'?(k.n+'. '+D.short[k.n-1]):k.t==='judg'?'My seven calls':'What this is not'}
const SIDE=['L','L','B','B','B','B','R','R'],PHI=[170,147,124,101,79,56,33,10];
function build(){
  const nodes=$('nodes');nodes.innerHTML='';
  D.branches.forEach((b,i)=>{
    const el=document.createElement('div');el.className='br '+SIDE[i]+(open.has(b.id)?' open':'');el.id='b_'+b.id;
    el.style.animationDelay=(i*80)+'ms';
    el.innerHTML='<button class="ico" aria-label="'+esc(b.title)+'">'+b.icon+'</button>'
      +'<div class="lb"><button class="lab"><b>'+esc(b.title)+'</b><span>'+esc(b.sub)+'</span></button>'
      +'<div class="kids">'+b.kids.map((k,j)=>'<button class="pill '+(k.t==='judg'?'judg':k.t==='limits'?'limit':'')+(seen.has(key(k))?' seen':'')+'" data-b="'+b.id+'" data-j="'+j+'">'+esc(label(k))+'</button>').join('')+'</div></div>';
    nodes.appendChild(el);
    const t=()=>toggle(b.id);el.querySelector('.ico').onclick=t;el.querySelector('.lab').onclick=t;
    el.querySelectorAll('.pill').forEach(p=>p.onclick=()=>openItem(ALL.findIndex(a=>a.b===p.dataset.b&&a.k===b.kids[+p.dataset.j])));
  });
  prog();layout(true);
}
let SC=1;
function layout(anim){
  const m=root.classList.contains('m'),st=$('stage'),sc=$('sc');
  if(!m){SC=Math.min(1,st.clientWidth/1100);sc.style.transform='scale('+SC+')';sc.style.height=(st.clientHeight/SC)+'px'}
  D.branches.forEach((b,i)=>{
    const el=$('b_'+b.id);if(!el)return;
    if(m){el.style.left='';el.style.top='';el.querySelector('.lb').style.width='';return}
    const W=1100,H=st.clientHeight/SC,cx=W/2,cy=82;
    const Rx=Math.min(W*0.33,380),Ry=Math.max(150,H-cy-150),a=PHI[i]*Math.PI/180;
    const x=cx+Rx*Math.cos(a),y=cy+Ry*Math.sin(a);
    el.style.left=x+'px';el.style.top=y+'px';
    if(SIDE[i]!=='B'){const av=(SIDE[i]==='L'?x:W-x)-40-8;el.querySelector('.lb').style.width=Math.max(110,Math.min(190,av))+'px'}
  });
  lines(anim);
}
function toggle(id,force){
  const on=force===undefined?!open.has(id):force;on?open.add(id):open.delete(id);
  $('b_'+id).classList.toggle('open',on);const l=$('l_'+id);if(l)l.classList.toggle('on',on);
}
function prog(){$('prog').textContent='Explored '+seen.size+' of '+ALL.length}
function lines(anim){
  const svg=$('ln');if(root.classList.contains('m')){svg.innerHTML='';return}
  const s=$('sc').getBoundingClientRect(),h=document.querySelector('.hub').getBoundingClientRect();
  const hx=(h.left+h.width/2-s.left)/SC,hy=(h.top+h.height/2-s.top)/SC;let out='';
  D.branches.forEach(b=>{
    const ic=document.querySelector('#b_'+b.id+' .ico').getBoundingClientRect();
    const x=(ic.left+ic.width/2-s.left)/SC,y=(ic.top+ic.height/2-s.top)/SC,dx=hx-x,dy=hy-y,d=Math.hypot(dx,dy)||1;
    const px=x+dx/d*38,py=y+dy/d*38;
    out+='<line id="l_'+b.id+'" class="'+(open.has(b.id)?'on':'')+'" x1="'+hx+'" y1="'+hy+'" x2="'+px+'" y2="'+py+'"/><circle cx="'+px+'" cy="'+py+'" r="6"/>';
  });
  svg.innerHTML=out;
  if(anim)svg.querySelectorAll('line').forEach((p,i)=>{const L=Math.hypot(p.x2.baseVal.value-p.x1.baseVal.value,p.y2.baseVal.value-p.y1.baseVal.value);
    p.style.strokeDasharray=L;p.style.strokeDashoffset=L;
    setTimeout(()=>{p.style.transition='stroke-dashoffset .8s ease,stroke .2s,stroke-width .2s';p.style.strokeDashoffset=0},80+i*60)});
}
function research(){
  const col=(arr,cls)=>arr.map(([n,l])=>'<details class="rb '+cls+'"><summary>'+esc(n)+'</summary><ul>'+l.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul></details>').join('');
  return '<div class="out"><h4>Research mind map</h4><div class="mini"><button onclick="rb(true)">Expand all</button><button onclick="rb(false)">Collapse all</button></div>'
   +'<div class="rm"><div><h5>Researched</h5>'+col(D.done,'dn2')+'</div><div><h5>Still to research</h5>'+col(D.todo,'td')+'</div></div>'
   +'<div class="ai-cap">Green: researched, written up in PRD Section 13. Amber: listed in the PRD as still to research or confirm. Vendor claims still need checking with the vendor.</div></div>';
}
window.rb=v=>document.querySelectorAll('details.rb').forEach(d=>d.open=v);
function openItem(i){
  if(i<0||i>=ALL.length)return;cur=i;const {b,k}=ALL[i];seen.add(key(k));toggle(b,true);
  let h='',t='',n='';
  if(k.t==='step'){
    const s=D.steps[k.n-1];n=k.n;t=s.title;
    h='<div class="cols"><div class="cc me"><h4>What I asked</h4><q>'+esc(s.me)+'</q></div>'
     +'<div class="cc ai"><h4>What the AI did</h4><ul>'+s.ai.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul></div>'
     +'<div class="cc dec"><h4>What I decided</h4><ul>'+s.dec.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul></div></div>';
    h+='<div class="out"><h4>Output</h4><span class="ai-pill">'+esc(s.out)+'</span></div>';
    if(k.n===2)h+=research();else if(D.outputs[k.n])h+='<div class="out">'+D.outputs[k.n]+'</div>';
  }else if(k.t==='judg'){n='⚖';t='Seven calls that were mine';
    h='<p>The AI did a lot of the drafting and research. These are the decisions that were mine.</p>'+D.judg.map(([a,c])=>'<div class="jc"><b>'+esc(a)+'</b>'+esc(c)+'</div>').join('');
  }else{n='!';t='What this work is not';
    h='<p>Being clear about this is part of using AI well.</p>'+D.limits.map(x=>'<div class="lm">'+esc(x)+'</div>').join('');}
  $('dn').textContent=n;$('dt').textContent=t;$('db').innerHTML=h;$('db').scrollTop=0;
  $('pos').textContent=(i+1)+' of '+ALL.length;$('prev').disabled=i===0;$('next').disabled=i===ALL.length-1;
  root.classList.add('dopen');
  document.querySelectorAll('.pill').forEach(p=>{const bb=D.branches.find(x=>x.id===p.dataset.b);if(seen.has(key(bb.kids[+p.dataset.j])))p.classList.add('seen')});
  prog();
}
function closeD(){root.classList.remove('dopen')}
$('dx').onclick=closeD;$('scrim').onclick=closeD;
$('prev').onclick=()=>openItem(cur-1);$('next').onclick=()=>openItem(cur+1);
$('tour').onclick=()=>openItem(0);
$('exp').onclick=()=>{D.branches.forEach(b=>toggle(b.id,true))};
$('col').onclick=()=>{D.branches.forEach(b=>toggle(b.id,false))};
document.addEventListener('keydown',e=>{if(!root.classList.contains('dopen'))return;
  if(e.key==='Escape')closeD();if(e.key==='ArrowRight')openItem(cur+1);if(e.key==='ArrowLeft')openItem(cur-1)});
const mq=matchMedia('(max-width:899px)');
function mode(){root.classList.toggle('m',mq.matches);root.classList.toggle('t',mq.matches&&window.innerWidth>=560);setTimeout(()=>layout(true),60)}
mq.addEventListener?mq.addEventListener('change',mode):mq.addListener(mode);window.addEventListener('resize',()=>setTimeout(()=>layout(false),50));
build();mode();
</script></body></html>"""


def page(steps, judgment, limits, done, todo, outputs) -> str:
    branches = [{"id": i, "title": t, "sub": s, "icon": e, "side": side,
                 "kids": [{"t": k[0], **({"n": k[1]} if len(k) > 1 else {})} for k in kids]}
                for i, t, s, e, side, kids in BRANCHES]
    data = {"branches": branches, "short": SHORT,
            "steps": [{k: s[k] for k in ("title", "me", "ai", "dec", "out")} for s in steps],
            "judg": [list(j) for j in judgment], "limits": list(limits),
            "done": [[n, list(v)] for n, v in done], "todo": [[n, list(v)] for n, v in todo],
            "outputs": {str(k): v for k, v in outputs.items()}}
    blob = json.dumps(data).replace("</", "<\\/")
    return PAGE.replace("__DATA__", blob)
