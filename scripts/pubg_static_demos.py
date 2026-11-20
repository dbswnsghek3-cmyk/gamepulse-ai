"""정적 보고서(GitHub Pages)용 PUBG 시연 A·B·C — 서버 없이 브라우저에서 바로 조작.

Streamlit 앱과 같은 data/pubg/newstart.json 값을 쓰고, 계산식은 gamepulse/sim/newstart_sim.py 와 같다.
export_static.py 가 04 탭의 해당 하위 탭 끝에 덧붙인다.
"""

from __future__ import annotations

import json
from pathlib import Path

CSS = """<style>
.sx-live{border:1px solid #E2E8F0;border-radius:12px;background:#fff;padding:.8rem .9rem;margin:.8rem 0 1rem;max-width:1040px}
.sx-live h5{margin:0 0 .5rem;font-size:1rem;color:#1E293B}.sx-live h5 small{font-weight:600;color:#475569;margin-left:.4rem}
.sx-live .ctl{display:flex;flex-wrap:wrap;gap:.5rem .9rem;align-items:end;margin-bottom:.5rem}
.sx-live label{display:flex;flex-direction:column;font-size:.85rem;color:#475569;gap:.2rem}
.sx-live input[type=number]{width:7.5rem;padding:.35rem .5rem;border:1px solid #CBD5E1;border-radius:8px;font-size:.95rem}
.sx-live input[type=range]{width:12rem}
.sx-live .seg{display:flex;flex-wrap:wrap;gap:.35rem}
.sx-live .seg button{border:1px solid #CBD5E1;background:#fff;border-radius:8px;padding:.35rem .75rem;font-size:.92rem;cursor:pointer;color:#1E293B}
.sx-live .seg button[aria-pressed=true]{background:#2563EB;border-color:#2563EB;color:#fff}
.sx-live.b .seg button[aria-pressed=true]{background:#E97870;border-color:#E97870}
@media (max-width:640px){.sx-live input[type=range]{width:100%}.sx-live label{width:100%}}
</style>"""


def demos(root: Path) -> dict[str, str]:
    ns = json.loads((root / "data" / "pubg" / "newstart.json").read_text(encoding="utf-8"))
    dm, fb, bm = ns["demo_matches"], ns["demo_feedback"], ns["bm_sim"]
    data = json.dumps({"m": dm["rows"], "fb": fb, "bm": bm}, ensure_ascii=False)

    a = f"""{CSS}<div class="sx-live" id="lvA"><h5>이 페이지에서 바로 조작 · 시연 A <small>예시 데이터</small></h5>
<div class="seg" id="lvA-seg">{''.join(f'<button type="button" data-k="{i}" aria-pressed="{str(i == 5).lower()}">{i}경기</button>' for i in range(1, 11))}</div>
<div class="pg-demo" style="margin-top:.8rem"><h4 id="lvA-h">5경기째 기록</h4><div class="pg-metric" id="lvA-m"></div><div class="act" id="lvA-g"></div>
<div class="src">{dm['note']} · 지표는 기존 텔레메트리(위치·기절·부활)로 계산 가능</div></div></div>"""

    b = f"""<div class="sx-live" id="lvB"><h5>이 페이지에서 바로 조작 · 시연 B <small>상황을 고르면 피드백이 바뀝니다</small></h5>
<div class="seg" id="lvB-seg">{''.join(f'<button type="button" data-k="{i}" aria-pressed="{str(i == 0).lower()}">{f["label"]}</button>' for i, f in enumerate(fb))}</div>
<div class="pg-demo" style="margin-top:.8rem"><h4>첫 실전 피드백</h4><div class="src" id="lvB-s"></div><div id="lvB-p"></div>
<div class="act" id="lvB-a"></div><div class="src" id="lvB-d"></div></div></div>"""

    c = f"""<div class="sx-live b" id="lvC"><h5>이 페이지에서 바로 조작 · 시연 C <small>값을 바꾸면 바로 다시 계산</small></h5>
<div class="ctl"><label>1회 가격 (G-Coin)<input type="number" id="lvC-price" value="{bm['price']}" min="100" step="100"></label>
<label>목표 스킨 확률 <b id="lvC-pv">{bm['prob']}%</b><input type="range" id="lvC-prob" min="0.1" max="10" step="0.1" value="{bm['prob']}"></label>
<label>구매 횟수 <b id="lvC-nv">100회</b><input type="range" id="lvC-n" min="1" max="400" step="1" value="100"></label></div>
<div class="ctl"><label>1회당 스크랩<input type="number" id="lvC-spo" value="{bm['scrap_per_open']}" min="0"></label>
<label>교환 필요 스크랩<input type="number" id="lvC-ex" value="{bm['exchange_scrap']}" min="0" step="100"></label>
<label>보유 스크랩<input type="number" id="lvC-own" value="0" min="0" step="100"></label></div>
<div class="pg-demo b"><h4>목표 스킨까지 예상 비용 (가정 계산)</h4><div class="pg-metric" id="lvC-m"></div>
<div class="sx-chart-c" id="lvC-chart" style="height:280px"></div>
<div class="src">가격 1,800: {bm['notes']['price']} · 확률: {bm['notes']['prob']} · 스크랩 10/회: {bm['notes']['scrap_per_open']} · 교환가: {bm['notes']['exchange_scrap']}</div></div></div>"""

    js = """<script>(function(){var D=""" + data + """;
function f(x){return Math.round(x).toLocaleString('ko-KR');}
function seg(id,cb){var s=document.getElementById(id);if(!s)return;s.querySelectorAll('button').forEach(function(b){b.addEventListener('click',function(){
 s.querySelectorAll('button').forEach(function(x){x.setAttribute('aria-pressed','false');});b.setAttribute('aria-pressed','true');cb(+b.dataset.k);});});}
function A(k){var r=D.m[k-1],r0=D.m[0];function dl(v,v0,u){if(k==1)return'';var d=v-v0;return '<em>'+(d>0?'+':'')+d.toFixed(1)+u+' vs 1경기</em>';}
 document.getElementById('lvA-h').textContent=k+'경기째 기록';
 document.getElementById('lvA-m').innerHTML='<div><small>생존 시간</small><b>'+r[1].toFixed(1)+'분</b>'+dl(r[1],r0[1],'분')+'</div>'+
 '<div><small>첫 교전</small><b>'+(r[2]?'참여':'없음')+'</b><small>거리 '+(r[3]==null?'—':r[3]+'m')+'</small></div>'+
 '<div><small>팀원과 평균 거리</small><b>'+r[4]+'m</b>'+dl(r[4],r0[4],'m')+'</div><div><small>부활</small><b>'+r[5]+'회</b></div><div><small>순위</small><b>'+r[6]+'위</b></div>';
 document.getElementById('lvA-g').textContent='다음 목표 · '+r[7];}
function B(i){var x=D.fb[i];document.getElementById('lvB-s').textContent='상황 (예시) · '+x.scene;
 document.getElementById('lvB-p').innerHTML='<b>원인</b> '+x.problem;document.getElementById('lvB-a').textContent=x.action;
 document.getElementById('lvB-d').innerHTML='판정 데이터 · '+x.data+'<br>적용 단계 · <b>'+x.mvp+'</b>';}
function C(){var g=function(id){return +document.getElementById(id).value;};var price=g('lvC-price'),pp=g('lvC-prob'),n=g('lvC-n'),spo=g('lvC-spo'),ex=g('lvC-ex'),own=g('lvC-own');
 document.getElementById('lvC-pv').textContent=pp+'%';document.getElementById('lvC-nv').textContent=n+'회';
 var p=pp/100,cap=(spo>0&&ex>0)?Math.max(0,Math.ceil((ex-own)/spo)):null;
 function within(k,c){if(c!==null&&k>=c)return 1;return 1-Math.pow(1-p,k);}
 function opens(q){var k=Math.ceil(Math.log(1-q)/Math.log(1-Math.min(p,0.999999)));return cap!==null?Math.min(k,cap):k;}
 var eo=cap===null?1/p:(cap===0?0:(1-Math.pow(1-p,cap))/p),o50=opens(0.5),o90=opens(0.9);
 document.getElementById('lvC-m').innerHTML='<div><small>'+n+'회 안에 얻을 확률</small><b class="big">'+(within(n,cap)*100).toFixed(1)+'%</b></div>'+
 '<div><small>기대 비용 (교환 포함)</small><b>'+f(eo*price)+'</b><small>G-Coin · '+Math.round(eo)+'회</small></div>'+
 '<div><small>50% 도달</small><b>'+f(o50*price)+'</b><small>'+o50+'회</small></div><div><small>90% 도달</small><b>'+f(o90*price)+'</b><small>'+o90+'회</small></div>'+
 '<div><small>교환 확정 (천장)</small><b>'+(cap===null?'없음':f(cap*price))+'</b><small>'+(cap===null?'':cap+'회')+'</small></div>';
 if(window.Plotly){var mx=Math.max(n,cap||0,o90||0)+20,xs=[],y1=[],y2=[];for(var k=0;k<=mx;k++){xs.push(k);y1.push((1-Math.pow(1-p,k))*100);y2.push(within(k,cap)*100);}
  Plotly.react('lvC-chart',[{x:xs,y:y1,name:'교환 없이',line:{color:'#94A3B8',dash:'dot',width:2}},{x:xs,y:y2,name:'스크랩 교환 포함',line:{color:'#E97870',width:3}}],
  {margin:{l:50,r:10,t:30,b:40},height:280,legend:{orientation:'h',y:1.12,x:0},xaxis:{title:'구매 횟수 (회)',range:[0,mx]},yaxis:{title:'획득 확률 (%)',range:[0,105],ticksuffix:'%'},
   shapes:[{type:'line',x0:n,x1:n,y0:0,y1:100,line:{dash:'dash',color:'#1E293B',width:1}}],paper_bgcolor:'#fff',plot_bgcolor:'#fff',font:{size:12}},{displayModeBar:false,responsive:true});}}
seg('lvA-seg',A);seg('lvB-seg',B);A(5);B(0);
['lvC-price','lvC-prob','lvC-n','lvC-spo','lvC-ex','lvC-own'].forEach(function(id){var e=document.getElementById(id);if(e)e.addEventListener('input',C);});
C();window.addEventListener('hashchange',function(){if(window.Plotly&&document.getElementById('lvC-chart'))Plotly.Plots.resize('lvC-chart');});
document.querySelectorAll('.ow-tabbar button').forEach(function(b){b.addEventListener('click',function(){setTimeout(function(){if(window.Plotly)Plotly.Plots.resize('lvC-chart');},50);});});
})();</script>"""
    return {"시연 A · 첫 10경기 성장 기록": a, "시연 B · 첫 실전 피드백 (A1)": b, "시연 C · 총비용 시뮬레이터 (B1)": c + js}
