"""정적 보고서(GitHub Pages)용 PUBG 페이지 보강 — 서버 없이 브라우저에서 바로 조작.

- 시연 A·B·C·B2: Streamlit '제안' 칸과 같은 구성(입력 → 결과 카드)을 JavaScript 로 구현한다.
  같은 data/pubg/newstart.json 값을 쓰고, 계산식은 gamepulse/sim/newstart_sim.py 와 같다.
- export_static.py 가 04 탭의 해당 하위 탭 끝에 덧붙이면, 아래 PAGE_JS 가 각 조작판을 그 하위 탭의 '제안' 칸
  (Streamlit 화면을 옮긴 스냅샷 자리)으로 옮긴다. 조작판은 처음에 hidden 이라 JavaScript 가 없으면
  스냅샷(앱 기본 화면과 같은 글자)만 보이고 같은 내용이 두 번 나오지 않는다.
- PAGE_CSS / PAGE_JS 는 pubg.html 에만 들어간다 (오버워치 페이지는 그대로).
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

B_SAMPLE = '<span class="gp-badge k-sample">예시 데이터</span>'
B_SIM = '<span class="gp-badge k-sim">가정 시뮬레이션</span>'
B_MOCK = '<span class="gp-badge k-mock">기획 시안</span>'

PAGE_CSS = """<style>
/* ---- PUBG 정적 페이지 전용 (Streamlit 화면과 맞춤) ---- */
.pg-static{max-width:940px;margin:0 auto}   /* Streamlit 본문 폭(1400px 화면 기준 940px)과 같게 → 카드 줄바꿈·글자 밀도 동일 */
.pg-static .pg-cards{grid-template-columns:repeat(3,minmax(0,1fr))}
@media (max-width:900px){.pg-static .pg-cards{grid-template-columns:1fr}}
.pg-static.js .sx-tabs>.sx-tabnav{gap:1.4rem;background:none;border-bottom:1px solid #E2E8F0;padding:0;margin:.4rem 0 1rem}
.pg-static.js .sx-tabs>.sx-tabnav a{background:none;border-radius:0;color:#334155;padding:.55rem 0;border-bottom:2px solid transparent;margin-bottom:-1px;font-size:.92rem}
.pg-static.js .sx-tabs>.sx-tabnav a.on{color:#2563EB;border-bottom-color:#2563EB;font-weight:600}
.pg-static.js .sx-tabs>.sx-tab>.sx-tab-h{display:none}
.pg-static.js .sx-tabs>.sx-tab{margin-bottom:.5rem}
.pg-live .ctl{display:flex;flex-wrap:wrap;gap:.5rem 1rem;align-items:end;margin:.1rem 0 .7rem}
.pg-live label{display:flex;flex-direction:column;font-size:.86rem;color:#31333F;gap:.3rem;min-width:9rem;flex:1 1 9rem}
.pg-live label b{color:#E97870;font-weight:700}
.pg-live input[type=number]{width:100%;box-sizing:border-box;padding:.45rem .6rem;border:1px solid #D5DAE5;border-radius:8px;font-size:.95rem;background:#F0F2F6}
.pg-live input[type=range]{width:100%;accent-color:#E97870}
.pg-live.a input[type=range]{accent-color:#2563EB}
.pg-live .seg-l{font-size:.86rem;color:#31333F;margin:.1rem 0 .35rem}
.pg-live .seg{display:flex;flex-wrap:wrap;gap:.35rem;margin-bottom:.7rem}
.pg-live .seg button{border:1px solid #D5DAE5;background:#fff;border-radius:999px;padding:.3rem .8rem;font-size:.88rem;cursor:pointer;color:#31333F;font-family:inherit}
.pg-live .seg button[aria-pressed=true]{background:#2563EB;border-color:#2563EB;color:#fff}
.pg-live .tog{display:flex;align-items:center;gap:.5rem;font-size:.88rem;color:#31333F;margin:.7rem 0 .3rem;cursor:pointer;flex-direction:row;min-width:0}
.pg-live .tog input{width:2.2rem;height:1.2rem;accent-color:#2563EB}
.pg-live .info{background:#E8F0FE;color:#1E3A8A;border-radius:8px;padding:.6rem .8rem;font-size:.9rem;margin-top:.4rem}
.pg-live .hint{font-size:.75rem;color:#64748B;margin:.4rem 0 0}
.pg-live ul{margin:.6rem 0;padding-left:1.2rem;font-size:.88rem;color:#334155;line-height:1.6}
.pg-live table{border-collapse:collapse;font-size:.88rem;margin-top:.4rem}
.pg-live th,.pg-live td{border-bottom:1px solid #E2E8F0;padding:.3rem .8rem;text-align:right}
.pg-live th:first-child,.pg-live td:first-child{text-align:left}
.pg-shotlist{display:flex;flex-wrap:wrap;gap:.4rem;margin:.3rem 0 1rem;font-size:.85rem;align-items:center}
.pg-shotlist a{padding:.2rem .6rem;border:1px solid #CBD5E1;border-radius:999px;text-decoration:none;color:#1E5EFF;background:#fff}
.pg-screen img{width:100%;height:auto;border:1px solid #E2E8F0;border-radius:8px}
</style>"""

PAGE_JS = """<script>(function(){
  var root=document.querySelector('.pg-static'); if(!root) return; root.classList.add('js');
  /* 하위 탭 (시연 A·B·C·B2): 선택한 1개만 표시 · JavaScript 가 없으면 전부 펼쳐 둔다 */
  root.querySelectorAll('.sx-tabs').forEach(function(t){
    var links=[].slice.call(t.querySelectorAll(':scope>.sx-tabnav>a')), secs=[].slice.call(t.querySelectorAll(':scope>.sx-tab'));
    function show(i){ secs.forEach(function(s,j){ s.hidden=(i!==j); }); links.forEach(function(a,j){ a.classList.toggle('on', i===j); a.setAttribute('aria-selected', String(i===j)); });
      if(window.Plotly) secs[i].querySelectorAll('.sx-chart-c').forEach(function(c){ if(!c.closest('details:not([open])')) try{Plotly.Plots.resize(c);}catch(e){} }); }
    links.forEach(function(a,j){ a.setAttribute('role','tab'); a.addEventListener('click',function(e){ e.preventDefault(); show(j); }); });
    if(secs.length) show(0);
  });
  /* 조작판을 '제안' 칸(스냅샷)과 바꾸기 */
  root.querySelectorAll('[data-pg-mount]').forEach(function(el){
    var sec=el.closest('.sx-tab'); if(!sec) return;
    if(el.getAttribute('data-pg-mount')==='mock'){
      var h=sec.querySelector('.ow-colh.mock'), col=h&&h.closest('.sx-col'); if(!col) return;
      [].slice.call(col.children).forEach(function(c){ if(!c.contains(h)) c.remove(); });
      col.appendChild(el);
    } else {
      var d=[].slice.call(sec.querySelectorAll('details.sx-exp')).filter(function(x){ return !x.closest('.sx-col') && !x.hasAttribute('data-pg-mount'); })[0];
      if(d) d.replaceWith(el); else sec.appendChild(el);
    }
    el.hidden=false;
  });
  document.dispatchEvent(new Event('pg-mounted'));
})();</script>"""


def demos(root: Path) -> dict[str, str]:
    ns = json.loads((root / "data" / "pubg" / "newstart.json").read_text(encoding="utf-8"))
    dm, fb, bm, salvage = ns["demo_matches"], ns["demo_feedback"], ns["bm_sim"], ns["salvage"]
    data = json.dumps({"m": dm["rows"], "fb": fb, "bm": bm, "sv": salvage}, ensure_ascii=False).replace("</", "<\\/")
    hint = '<div class="hint">이 페이지에서 직접 조작 · 값을 바꾸면 바로 다시 계산 (JavaScript)</div>'

    seg_a = "".join(f'<button type="button" data-k="{i}" aria-pressed="{str(i == 5).lower()}">{i}</button>' for i in range(1, 11))
    a = (f'<div class="pg-live a" data-pg-mount="mock" hidden><div class="seg-l">경기 번호 (예시 계정)</div>'
         f'<div class="seg" id="lvA-seg">{seg_a}</div>'
         f'<div class="pg-demo"><h4><span id="lvA-h">5</span>경기째 성장 기록 {B_SAMPLE}</h4><div class="pg-metric" id="lvA-m"></div>'
         f'<div class="act" id="lvA-g"></div><div class="src">{escape(dm["note"])} · 보상 없음 (훈련소 미션과 구분)</div></div>{hint}</div>')

    seg_b = "".join(f'<button type="button" data-k="{i}" aria-pressed="{str(i == 0).lower()}">{escape(x["label"])}</button>'
                    for i, x in enumerate(fb))
    b = (f'<div class="pg-live a" data-pg-mount="mock" hidden><div class="seg-l">상황 선택</div>'
         f'<div class="seg" id="lvB-seg">{seg_b}</div>'
         f'<div class="pg-demo"><h4>첫 실전 피드백 {B_MOCK}</h4><div class="src" id="lvB-s"></div><div id="lvB-p"></div>'
         f'<div class="act" id="lvB-a"></div><div class="src" id="lvB-d"></div></div>'
         f'<label class="tog"><input type="checkbox" id="lvB-off"> 피드백 끄기</label>'
         f'<div class="info" id="lvB-info" hidden>피드백을 껐습니다. 결과 화면은 기존과 같습니다. (기획 시안)</div>{hint}</div>')

    c_top = (f'<div class="pg-live" data-pg-mount="mock" hidden><div class="ctl">'
             f'<label>1회 가격 (G-Coin · 예시)<input type="number" id="lvC-price" value="{bm["price"]}" min="100" max="10000" step="100"></label>'
             f'<label>목표 스킨 확률 (% · 예시) <b id="lvC-pv">{bm["prob"]}</b><input type="range" id="lvC-prob" min="0.1" max="10" step="0.1" value="{bm["prob"]}"></label></div>'
             f'<div class="pg-demo b"><h4>목표 스킨까지 예상 비용 {B_SAMPLE} {B_SIM}</h4><div class="pg-metric" id="lvC-m"></div>'
             '<div class="src">예시 데이터 계산 · 1회 200 G-Coin·확률 0.9%·교환가 3,000은 게임 화면 캡처값이며 공개 공식 문서로 확인되지 않음 '
             '(공지 가격 1,800 G-Coin과 불일치) · 첫 10회 1,000 G-Coin만 공식 공지 확인 · 출처는 아래 펼쳐보기</div></div>'
             f'{hint}</div>')
    c_exp = (f'<details class="sx-exp pg-live" data-pg-mount="exp" hidden><summary>자세히 보기 · 스크랩 교환 조건 · 구매 횟수별 확률 곡선 · 계산식 '
             f'<span class="sx-more">펼쳐보기</span></summary><div class="sx-exp-b"><div class="ctl">'
             f'<label>1회당 스크랩<input type="number" id="lvC-spo" value="{bm["scrap_per_open"]}" min="0" max="100"></label>'
             f'<label>교환 필요 스크랩<input type="number" id="lvC-ex" value="{bm["exchange_scrap"]}" min="0" max="20000" step="100"></label>'
             f'<label>보유 스크랩<input type="number" id="lvC-own" value="0" min="0" max="20000" step="100"></label>'
             f'<label>구매 횟수 <b id="lvC-nv">100</b><input type="range" id="lvC-n" min="1" max="400" step="1" value="100"></label></div>'
             f'<div class="ctl"><label>첫 묶음 횟수 (0 = 할인 미적용)<input type="number" id="lvC-fn" value="{bm.get("first_n", 0)}" min="0" max="100"></label>'
             f'<label>첫 묶음 가격 (G-Coin)<input type="number" id="lvC-fp" value="{bm.get("first_price", 0)}" min="0" step="100"></label>'
             f'<span style="flex:2 1 9rem"></span></div>'
             f'<div class="ow-tiles" id="lvC-t"></div>'
             f'<div class="ow-chart-h"><div class="ow-chart-t">{B_SIM} 구매 횟수별 획득 확률</div><div class="ow-chart-u">% · 코랄 = 교환 포함</div></div>'
             f'<div class="sx-chart-c" id="lvC-chart" style="height:280px"></div>'
             f'<div class="ow-chart-b">P(n회 내) = 1 − (1 − p)^n · 천장 = 교환 스크랩 ÷ 1회당 스크랩</div><ul>'
             '<li>기대 구매 횟수 = (1 − (1 − p)^K) ÷ p (K = 천장 = 교환 스크랩 ÷ 1회당 스크랩, 교환이 없으면 1 ÷ p)</li>'
             '<li>비용 = 첫 구매는 10회 묶음 할인가, 이후 1회 가격 × 추가 횟수 → 기대 비용 = 묶음가 + 1회 가격 × (E[N] − E[min(N, 10)])</li>'
             '<li>중복 보상의 분해·토큰 환급은 반영하지 않음 → 실제 부담은 이보다 낮을 수 있다</li>'
             f'<li>1회 가격 {bm["price"]:,}: {escape(bm["notes"]["price"])}</li>'
             f'<li>첫 10회 {bm["first_price"]:,}: {escape(bm["notes"]["first"])}</li>'
             f'<li>확률 {bm["prob"]}%: {escape(bm["notes"]["prob"])}</li>'
             f'<li>스크랩 {bm["scrap_per_open"]}/회: {escape(bm["notes"]["scrap_per_open"])} · 교환가 {bm["exchange_scrap"]:,}: '
             f'{escape(bm["notes"]["exchange_scrap"])}</li></ul></div></details>')

    b2 = (f'<div class="pg-live" data-pg-mount="mock" hidden><div class="ctl">'
          f'<label>현재 레벨 <b id="lvU-cv">3</b><input type="range" id="lvU-cur" min="1" max="10" step="1" value="3"></label>'
          f'<label>목표 레벨 <b id="lvU-tv">10</b><input type="range" id="lvU-tgt" min="1" max="10" step="1" value="10"></label></div>'
          f'<div class="ctl"><label>보유 폴리머<input type="number" id="lvU-pol" value="5000" min="0" max="100000" step="500"></label>'
          f'<label>보유 설계도<input type="number" id="lvU-sch" value="10" min="0" max="200"></label></div>'
          f'<div class="pg-demo b"><h4><span id="lvU-h"></span> {B_SIM}</h4><div class="pg-metric" id="lvU-m"></div>'
          f'<div class="src">획득 경로 · 성장형 스킨 분해 · 이벤트 패키지 · 누적 개봉 보상 (공식)</div></div>'
          f'<details class="sx-exp" id="lvU-d"><summary>자세히 보기 · 단계별 추정 필요량 <span class="sx-more">펼쳐보기</span></summary>'
          f'<div class="sx-exp-b"><div class="ow-table-b">{B_SIM}</div><table id="lvU-tb"></table></div></details>{hint}</div>')

    js = """<script>(function(){var D=""" + data + """;
function f(x){return Math.round(x).toLocaleString('ko-KR');}
function $(id){return document.getElementById(id);}
function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function seg(id,cb){var s=$(id);if(!s)return;s.querySelectorAll('button').forEach(function(b){b.addEventListener('click',function(){
 s.querySelectorAll('button').forEach(function(x){x.setAttribute('aria-pressed','false');});b.setAttribute('aria-pressed','true');cb(+b.dataset.k);});});}
/* 시연 A · 첫 10경기 성장 기록 (Streamlit demo_a 와 같은 지표 3개) */
function A(k){var r=D.m[k-1],r0=D.m[0];function dl(v,v0,u){if(k==1)return'';var d=v-v0;return '<em>'+(d>0?'+':'')+d.toFixed(1)+u+' vs 1경기</em>';}
 $('lvA-h').textContent=k;
 $('lvA-m').innerHTML='<div><small>생존 시간</small><b>'+r[1].toFixed(1)+'분</b>'+dl(r[1],r0[1],'분')+'</div>'+
 '<div><small>첫 교전</small><b>'+(r[2]?'참여':'없음')+'</b><small>거리 '+(r[3]==null?'—':Math.round(r[3])+'m')+'</small></div>'+
 '<div><small>팀원과 거리</small><b>'+Math.round(r[4])+'m</b>'+dl(r[4],r0[4],'m')+'</div>';
 $('lvA-g').textContent='다음 목표 · '+r[7];}
/* 시연 B · 첫 실전 피드백 (A1) */
function B(i){var x=D.fb[i];$('lvB-s').textContent='상황 (예시) · '+x.scene;
 $('lvB-p').innerHTML='<b>원인</b> '+esc(x.problem);$('lvB-a').textContent=x.action;
 $('lvB-d').innerHTML='판정 데이터 · '+esc(x.data)+' · <b>'+esc(x.mvp)+'</b>';}
/* 시연 C · 총비용 시뮬레이터 (B1) · gamepulse/sim/newstart_sim.py crate_summary 와 같은 식 */
function C(){var g=function(id){return +$(id).value;};var price=g('lvC-price'),pp=g('lvC-prob'),n=g('lvC-n'),spo=g('lvC-spo'),ex=g('lvC-ex'),own=g('lvC-own'),fn=g('lvC-fn'),fp=g('lvC-fp');
 $('lvC-pv').textContent=pp.toFixed(1);$('lvC-nv').textContent=n;
 var p=pp/100,cap=(spo>0&&ex>0)?Math.max(0,Math.ceil((ex-own)/spo)):null;
 function within(k,c){if(c!==null&&k>=c)return 1;if(p<=0)return 0;return 1-Math.pow(1-Math.min(p,1),Math.max(k,0));}
 function opens(q){if(p<=0)return cap;var k=Math.ceil(Math.log(1-q)/Math.log(1-Math.min(p,0.999999)));return cap!==null?Math.min(k,cap):k;}
 function eN(c){if(c!==null&&c===0)return 0;if(p<=0)return c!==null?c:Infinity;return c===null?1/p:(1-Math.pow(1-p,c))/p;}
 function cost(k){if(k===null)return null;if(fn<=0||k<=0)return Math.max(k,0)*price;return fp+Math.max(k-fn,0)*price;}
 function ecost(e,c){if(fn<=0)return e*price;var m=c===null?fn:Math.min(c,fn);return ((c===null||c>0)?fp:0)+price*(e-eN(m));}
 var eo=eN(cap),o50=opens(0.5),o90=opens(0.9);
 $('lvC-m').innerHTML='<div><small>기대 비용 (교환 포함)</small><b class="big">'+f(ecost(eo,cap))+'</b><small>G-Coin · 평균 '+Math.round(eo)+'회</small></div>'+
 '<div><small>50% 확률 도달</small><b>'+f(cost(o50)||0)+'</b><small>'+o50+'회</small></div><div><small>90% 확률 도달</small><b>'+f(cost(o90)||0)+'</b><small>'+o90+'회</small></div>';
 function tile(l,v,s){return '<div class="ow-tile"><div class="ow-tile-l">'+l+'</div><div class="ow-tile-v">'+v+'</div><div class="ow-tile-s">'+s+'</div></div>';}
 $('lvC-t').innerHTML=tile(n+'회 안에 얻을 확률',(within(n,cap)*100).toFixed(1)+'%','독립 시행 · '+n+'회 비용 '+f(cost(n))+' G-Coin')+
  tile('교환 확정 (천장)',cap===null?'없음':f(cost(cap)),cap===null?'':cap+'회 · G-Coin')+
  tile('교환 없을 때 기대 비용',f(ecost(eN(null),null)),'G-Coin · 1 ÷ p 회');
 if(window.Plotly){var mx=Math.max(n,cap||0,o90||0)+20,xs=[],y1=[],y2=[];for(var k=0;k<=mx;k++){xs.push(k);y1.push(within(k,null)*100);y2.push(within(k,cap)*100);}
  Plotly.react('lvC-chart',[{x:xs,y:y1,name:'교환 없이',line:{color:'#94A3B8',dash:'dot',width:2}},{x:xs,y:y2,name:'스크랩 교환 포함',line:{color:'#E97870',width:3}}],
  {margin:{l:56,r:10,t:30,b:44},height:280,legend:{orientation:'h',y:1.12,x:0},xaxis:{title:{text:'구매 횟수 (회)'},range:[0,mx]},yaxis:{title:{text:'1번 이상 얻을 확률 (%)'},range:[0,105],ticksuffix:'%'},
   paper_bgcolor:'#fff',plot_bgcolor:'#fff',font:{size:12,family:"Pretendard, 'Noto Sans KR', 'Malgun Gothic', sans-serif"}},{displayModeBar:false,responsive:true});}}
/* 강화 비용 안내 (B2 · 추정) · upgrade_need 와 같은 식 (분해 환급표 = 누적 투입량 가정) */
function U(){var cur=+$('lvU-cur').value,tgt=+$('lvU-tgt').value,pol=+$('lvU-pol').value,sch=+$('lvU-sch').value;$('lvU-cv').textContent=cur;$('lvU-tv').textContent=tgt;
 var T={};D.sv.forEach(function(r){T[r[0]]=[r[1],r[2]];});var np=0,ns=0,steps=[];
 if(tgt>cur){np=T[tgt][0]-T[cur][0];ns=T[tgt][1]-T[cur][1];for(var lv=cur+1;lv<=tgt;lv++)steps.push([lv,T[lv][0]-T[lv-1][0],T[lv][1]-T[lv-1][1]]);}
 $('lvU-h').textContent=cur+' → '+tgt+'레벨 필요 재료 (추정)';
 $('lvU-m').innerHTML='<div><small>폴리머</small><b>'+f(np)+'</b><small>부족 '+f(Math.max(0,np-pol))+'</small></div><div><small>설계도</small><b>'+f(ns)+'</b><small>부족 '+f(Math.max(0,ns-sch))+'</small></div>';
 $('lvU-d').hidden=!steps.length;
 $('lvU-tb').innerHTML='<tr><th>레벨</th><th>폴리머</th><th>설계도</th></tr>'+steps.map(function(s){return '<tr><td>'+(s[0]-1)+'→'+s[0]+'</td><td>'+f(s[1])+'</td><td>'+s[2]+'</td></tr>';}).join('');}
function init(){seg('lvA-seg',A);seg('lvB-seg',B);A(5);B(0);
 $('lvB-off').addEventListener('change',function(){$('lvB-info').hidden=!this.checked;});
 ['lvC-price','lvC-prob','lvC-n','lvC-spo','lvC-ex','lvC-own','lvC-fn','lvC-fp'].forEach(function(id){$(id).addEventListener('input',C);});
 ['lvU-cur','lvU-tgt','lvU-pol','lvU-sch'].forEach(function(id){$(id).addEventListener('input',U);});
 C();U();
 function rs(){setTimeout(function(){if(window.Plotly&&$('lvC-chart').offsetParent)Plotly.Plots.resize('lvC-chart');},60);}
 document.querySelectorAll('.ow-tabbar button,.sx-tabnav a').forEach(function(b){b.addEventListener('click',rs);});
 document.querySelectorAll('details').forEach(function(d){d.addEventListener('toggle',function(){if(d.open)rs();});});}
if(document.querySelector('.pg-static.js'))init();else document.addEventListener('pg-mounted',init);
})();</script>"""
    return {"시연 A · 첫 10경기 성장 기록": a, "시연 B · 첫 실전 피드백 (A1)": b,
            "시연 C · 총비용 시뮬레이터 (B1)": c_top + c_exp, "강화 비용 안내 (B2 · 추정)": b2 + js}
