"""정적 보고서(GitHub Pages)용 FC 온라인 데모 2개 (A1 구단 가치 분석기 · C 매칭 정책 비교) — 서버 없이 브라우저에서 조작.

Streamlit 데모 입력 칸 첫머리의 <div class="fc-anchor" data-k="…">를 찾아 그 행(.sx-row = 입력 칸 + 결과 칸)을
아래 조작판으로 바꾼다. JavaScript 가 없으면 Streamlit 기본 화면 스냅샷만 보인다. 계산식은 gamepulse/sim/fc_sim.py 와 같다.
"""

from __future__ import annotations

import json
from pathlib import Path

B_SIM = '<span class="gp-badge k-sim">가정 시뮬레이션</span>'

PAGE_EXTRA_CSS = """<style>
.fc-live .ctl{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.55rem 1rem;margin:.2rem 0 .8rem}
.fc-live label{display:flex;flex-direction:column;gap:.25rem;font-size:.88rem;color:#31333F}
.fc-live label b{color:#6D28D9}
.fc-live input[type=number],.fc-live select{padding:.45rem .6rem;border:1px solid #D5DAE5;border-radius:8px;font-size:.95rem;background:#F0F2F6;font-family:inherit}
.fc-live input[type=range]{accent-color:#15803D}
.fc-live .seg{display:flex;flex-wrap:wrap;gap:.35rem;grid-column:1/-1}
.fc-live .seg button{border:1px solid #D5DAE5;background:#fff;border-radius:999px;padding:.3rem .8rem;font-size:.88rem;cursor:pointer;font-family:inherit}
.fc-live .seg button[aria-pressed=true]{background:#15803D;border-color:#15803D;color:#fff}
.fc-live .hint{font-size:.75rem;color:#64748B;margin-top:.4rem}
@media(max-width:700px){.fc-live .ctl{grid-template-columns:1fr}}
</style>"""


def demos(root: Path) -> str:
    d = json.loads((root / "data" / "fconline" / "fc.json").read_text(encoding="utf-8"))
    pols = {p["key"]: {"fair": p["fair"], "ops": p["ops"]} for p in d["c_policies"]}
    hint = '<div class="hint">이 페이지에서 직접 조작 · 값을 바꾸면 바로 다시 계산 (JavaScript)</div>'
    a1 = ('<div class="fc-live" data-k="a1" hidden><div class="ctl">'
          '<label>초기 구단 가치 (억 BP · 가상)<input type="number" id="a1v" value="10" min="1" step="1"></label>'
          '<label>내 구단 가치 하락률 <b id="a1mv">50%</b><input type="range" id="a1m" min="0" max="90" value="50"></label>'
          '<label>시장 전체 하락률 <b id="a1kv">20%</b><input type="range" id="a1k" min="0" max="90" value="20"></label></div>'
          f'<div class="fc-demo"><h4>구단 가치 진단 {B_SIM}</h4><div class="fc-m" id="a1o"></div>'
          '<div class="fc-act"><b>가치가 떨어져도 능력치·팀컬러는 그대로</b> → 재건 플랜(A2)</div>'
          f'<div class="src">시세와 경기 성능은 다른 숫자 · 시세 보장 없음</div></div>{hint}</div>')
    c5 = ('<div class="fc-live" data-k="c5" hidden><div class="ctl"><div class="seg" id="c5p">'
          '<button type="button" data-k="1" aria-pressed="false">1안 · 완전 분리 매칭</button>'
          '<button type="button" data-k="2" aria-pressed="false">2안 · 선택형 동일 장치 우선 매칭</button>'
          '<button type="button" data-k="3" aria-pressed="true">3안 · 통합 유지 + 조작 환경 개선 (권고)</button></div>'
          '<label>키보드 이용자 비중 <b id="c5kv">50%</b><input type="range" id="c5k" min="5" max="95" value="50"></label>'
          '<label>동시 매칭 대기 인원 (명 · 가정)<input type="number" id="c5n" value="10000" min="100" step="500"></label>'
          '<label>랭크 구간<select id="c5r"><option value="0.05" selected>상위 랭크 (구간 비율 5% · 가정)</option>'
          '<option value="0.35">중위 랭크 (35% · 가정)</option><option value="0.6">일반 랭크 (60% · 가정)</option></select></label>'
          '<label>허용 대기시간 (통합 대비) <b id="c5av">2.0배</b><input type="range" id="c5a" min="1" max="5" step="0.5" value="2"></label>'
          '<label>동일 장치 우선 선택 비율 <b id="c5fv">40%</b><input type="range" id="c5f" min="0" max="100" value="40"></label></div>'
          f'<div class="fc-demo c"><h4>정책 비교 {B_SIM}</h4><div class="fc-cmp"><table id="c5t"></table></div><div class="fc-act" id="c5m"></div>'
          '<div class="src">실제 매칭 알고리즘이 아닌 단순 모델 · 대기시간은 실제 초가 아니라 통합 대비 상대 배수 · 공정성·운영 난이도는 정성 평가</div></div>'
          f'{hint}</div>')
    data = json.dumps(pols, ensure_ascii=False)
    js = """<script>(function(){var PO=""" + data + """;
function $(i){return document.getElementById(i);}
function bp(x){x=Math.round(x);var s=x<0?'−':'';x=Math.abs(x);var jo=Math.floor(x/1e12),eok=Math.floor((x%1e12)/1e8),man=Math.floor((x%1e8)/1e4);
 var p=[];if(jo)p.push(jo.toLocaleString('ko-KR')+'조');if(eok)p.push(eok.toLocaleString('ko-KR')+'억');if(man)p.push(man.toLocaleString('ko-KR')+'만');return s+(p.join(' ')||x.toLocaleString('ko-KR'))+' BP';}
function box(l,v,e,c,ec){return '<div><small>'+l+'</small><b class="'+(c||'')+'">'+v+'</b>'+(e?'<em class="'+(ec||'')+'">'+e+'</em>':'')+'</div>';}
function A(){var v0=+$('a1v').value*1e8,m=+$('a1m').value/100,k=+$('a1k').value/100;$('a1mv').textContent=$('a1m').value+'%';$('a1kv').textContent=$('a1k').value+'%';
 var now=v0*(1-m),need=m<1?m/(1-m)*100:Infinity,rel=((1-m)/(1-k)-1)*100;
 $('a1o').innerHTML=box('현재 구단 가치',bp(now),'−'+bp(v0-now).replace(' BP',''),'','dn')+box('원래대로 돌아가려면','+'+need.toFixed(0)+'%','상승 필요','up')+
  box('시장 대비',(rel>=0?'+':'')+rel.toFixed(0)+'%',rel<0?'시장보다 더 하락':'시장과 같거나 덜 하락');}
var NAME={'1':'완전 분리 매칭','2':'선택형 동일 장치 우선 매칭','3':'통합 유지 + 조작 환경 개선'},MSG={
 '1':'공정성 체감은 좋아질 수 있지만 소수 장치·상위 랭크의 대기시간이 먼저 흔들릴 위험',
 '2':'선택한 사람만 같은 장치 우선 · 허용 배수에 닿으면 통합으로 확대',
 '3':'매칭 풀은 그대로 · 키보드 조작 개선으로 격차가 줄어드는지 승률·조작 성공률로 검증'},pol='3';
function C(){var k=+$('c5k').value/100,n=+$('c5n').value,r=+$('c5r').value,al=+$('c5a').value,pf=+$('c5f').value/100;
 $('c5kv').textContent=$('c5k').value+'%';$('c5av').textContent=al.toFixed(1)+'배';$('c5fv').textContent=$('c5f').value+'%';
 var base=n*r,rows='<tr><th>정책</th><th>공정성 체감</th><th>상대 풀</th><th>대기시간 위험</th><th>운영 난이도</th></tr>';
 ['1','2','3'].forEach(function(key){var kb,pad;if(key==='1'){kb=base*k;pad=base*(1-k);}else if(key==='3'){kb=pad=base;}else{kb=pf>0?base*k*pf:base;pad=pf>0?base*(1-k)*pf:base;}
  var kx=kb>0?base/kb:Infinity,px=pad>0?base/pad:Infinity,fb=key==='2'&&Math.max(kx,px)>al;if(key==='2'){kx=Math.min(kx,al);px=Math.min(px,al);}
  var w=Math.max(kx,px),risk=fb?'주의 · 통합 확대':(w>al?'높음':(w>al*0.7?'주의':'낮음'));
  rows+='<tr class="'+(key===pol?'on':'')+'"><td><b>'+key+'안</b> '+NAME[key]+(key==='3'?' <em>권고</em>':'')+'</td><td>'+PO[key].fair+'</td><td>키보드 '+Math.round(kb).toLocaleString('ko-KR')+
   ' · 패드 '+Math.round(pad).toLocaleString('ko-KR')+'명</td><td class="'+(risk==='높음'?'dn':'')+'">'+risk+'<small>통합의 '+w.toFixed(1)+'배</small></td><td>'+PO[key].ops+'</td></tr>';});
 $('c5t').innerHTML=rows;$('c5m').innerHTML='<b>'+pol+'안 선택</b> · '+MSG[pol];}
function mount(){document.querySelectorAll('.fc-live').forEach(function(el){var a=document.querySelector('.fc-anchor[data-k="'+el.dataset.k+'"]');
  var row=a&&a.closest('.sx-row');if(row){row.replaceWith(el);el.hidden=false;}});
 ['a1v','a1m','a1k'].forEach(function(i){$(i).addEventListener('input',A);});
 ['c5k','c5n','c5r','c5a','c5f'].forEach(function(i){$(i).addEventListener('input',C);$(i).addEventListener('change',C);});
 $('c5p').querySelectorAll('button').forEach(function(b){b.addEventListener('click',function(){$('c5p').querySelectorAll('button').forEach(function(x){x.setAttribute('aria-pressed','false');});
  b.setAttribute('aria-pressed','true');pol=b.dataset.k;C();});});
 A();C();}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount);else mount();
})();</script>"""
    return PAGE_EXTRA_CSS + a1 + c5 + js
