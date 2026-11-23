"""정적 보고서(GitHub Pages)용 FC 온라인 데모 3개 — 서버 없이 브라우저에서 바로 조작.

Streamlit 화면의 데모 입력 칸 첫머리에 있는 <div class="fc-anchor" data-k="…">를 찾아, 그 행(.sx-row = 입력 칸 + 결과 칸)을
아래 조작판으로 바꾼다. JavaScript 가 없으면 Streamlit 기본 화면을 옮긴 스냅샷만 보인다.
계산식은 gamepulse/sim/fc_sim.py 와 같다.
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
.fc-live input[type=range]{accent-color:#6D28D9}
.fc-live .seg{display:flex;flex-wrap:wrap;gap:.35rem;grid-column:1/-1}
.fc-live .seg button{border:1px solid #D5DAE5;background:#fff;border-radius:999px;padding:.3rem .8rem;font-size:.88rem;cursor:pointer;font-family:inherit}
.fc-live .seg button[aria-pressed=true]{background:#15803D;border-color:#15803D;color:#fff}
.fc-live .tog{flex-direction:row;align-items:center}
.fc-live .hint{font-size:.75rem;color:#64748B;margin-top:.4rem}
@media(max-width:700px){.fc-live .ctl{grid-template-columns:1fr}}
</style>"""


def demos(root: Path) -> str:
    d = json.loads((root / "data" / "fconline" / "fc.json").read_text(encoding="utf-8"))
    steps = "".join(f'<option value="{p}"{" selected" if a == 7 else ""}>{a}→{b}강 ({p}%)</option>' for a, b, p in d["enhance_prob"])
    hint = '<div class="hint">이 페이지에서 직접 조작 · 값을 바꾸면 바로 다시 계산 (JavaScript)</div>'
    a1 = ('<div class="fc-live" data-k="a1" hidden><div class="ctl">'
          '<label>초기 구단 가치 (억 BP · 가상)<input type="number" id="a1v" value="10" min="1" step="1"></label>'
          '<label>내 구단 가치 하락률 <b id="a1mv">50%</b><input type="range" id="a1m" min="0" max="90" value="50"></label>'
          '<label>시장 전체 하락률 <b id="a1kv">20%</b><input type="range" id="a1k" min="0" max="90" value="20"></label></div>'
          f'<div class="fc-demo"><h4>구단 가치 진단 {B_SIM}</h4><div class="fc-m" id="a1o"></div>'
          '<div class="fc-act"><b>가치가 떨어져도 선수 능력치·팀컬러는 그대로다</b> → 경기력 목표로 다시 성장 (A2)</div>'
          f'<div class="src">자산 가치(시세)와 경기 성능(능력치)은 다른 숫자 · 시세 보장 없음</div></div>{hint}</div>')
    b1 = ('<div class="fc-live" data-k="b1" hidden><div class="ctl">'
          f'<label>강화 단계 (공식 확률)<select id="b1s">{steps}</select></label>'
          '<label>부스트 게이지 <b id="b1gv">100%</b><input type="range" id="b1g" min="0" max="100" value="100"></label>'
          '<label>현재 선수 가치 (만 BP)<input type="number" id="b1v" value="684" step="10"></label>'
          '<label>강화 비용 · 재료 가치 (만 BP · 가정)<input type="number" id="b1c" value="500" step="10"></label>'
          '<label>성공 시 예상 가치 (만 BP)<input type="number" id="b1w" value="11000" step="100"></label>'
          '<label>실패 시 잔존 가치 (만 BP · 가정)<input type="number" id="b1f" value="382" step="10"></label>'
          '<label class="tog"><input type="checkbox" id="b1p"> 보호 수단 사용 (실패해도 등급 유지 · 대상 제한)</label></div>'
          f'<div class="fc-demo b"><h4>이번 강화의 손익 {B_SIM}</h4><div class="fc-m" id="b1o1"></div><div class="fc-m" id="b1o2"></div>'
          '<div class="fc-act"><b>기대값이 0 근처여도, 대부분은 실패 쪽 결과를 겪는다</b> → 실패 직후 선택지(B2)가 필요</div>'
          '<div class="src">기본값 = 바조 카드 7강 → 8강 · 7강 684만·8강 1억 1,000만은 캡처 판매 최저가 · 실패 시 6강(382만)으로 복구된다고 가정 '
          f'(공식 복구 확률표는 이미지라 미확인) · 재료 비용은 가정</div></div>{hint}</div>')
    c5 = ('<div class="fc-live" data-k="c5" hidden><div class="ctl"><div class="seg" id="c5p">'
          '<button type="button" data-k="1" aria-pressed="false">1안 · 완전 분리 매칭</button>'
          '<button type="button" data-k="2" aria-pressed="false">2안 · 통합 유지 + 조작 밸런스 개선</button>'
          '<button type="button" data-k="3" aria-pressed="true">3안 · 선택형 동일 장치 우선 매칭</button></div>'
          '<label>키보드 이용자 비중 <b id="c5kv">50%</b><input type="range" id="c5k" min="5" max="95" value="50"></label>'
          '<label>동시 매칭 대기 인원 (명 · 가정)<input type="number" id="c5n" value="10000" min="100" step="500"></label>'
          '<label>랭크 구간<select id="c5r"><option value="0.05" selected>상위 랭크 (구간 비율 5% · 가정)</option>'
          '<option value="0.35">중위 랭크 (35% · 가정)</option><option value="0.6">일반 랭크 (60% · 가정)</option></select></label>'
          '<label>허용 대기시간 (통합 대비) <b id="c5av">2.0배</b><input type="range" id="c5a" min="1" max="5" step="0.5" value="2"></label>'
          '<label>동일 장치 매칭 선호 비율 <b id="c5fv">40%</b><input type="range" id="c5f" min="0" max="100" value="40"></label></div>'
          f'<div class="fc-demo c"><h4 id="c5h"></h4><div class="fc-m" id="c5o"></div><div class="fc-act" id="c5t"></div>'
          f'<div class="src" id="c5s"></div></div>{hint}</div>')
    js = """<script>(function(){
function $(i){return document.getElementById(i);}
function bp(x){x=Math.round(x);var s=x<0?'−':'';x=Math.abs(x);var jo=Math.floor(x/1e12),eok=Math.floor((x%1e12)/1e8),man=Math.floor((x%1e8)/1e4);
 var p=[];if(jo)p.push(jo.toLocaleString('ko-KR')+'조');if(eok)p.push(eok.toLocaleString('ko-KR')+'억');if(man)p.push(man.toLocaleString('ko-KR')+'만');return s+(p.join(' ')||x.toLocaleString('ko-KR'))+' BP';}
function box(l,v,e,c){return '<div><small>'+l+'</small><b class="'+(c||'')+'">'+v+'</b>'+(e?'<em>'+e+'</em>':'')+'</div>';}
function A(){var v0=+$('a1v').value*1e8,m=+$('a1m').value/100,k=+$('a1k').value/100;$('a1mv').textContent=$('a1m').value+'%';$('a1kv').textContent=$('a1k').value+'%';
 var now=v0*(1-m),need=m<1?m/(1-m)*100:Infinity,rel=((1-m)/(1-k)-1)*100;
 $('a1o').innerHTML=box('현재 구단 가치',bp(now),'−'+bp(v0-now).replace(' BP',''))+box('원래 가치로 돌아가려면','+'+need.toFixed(0)+'%','상승 필요','up')+
  box('시장 대비',(rel>=0?'+':'')+rel.toFixed(0)+'%',rel<0?'시장보다 더 하락':'시장과 같거나 덜 하락');}
function B(){var p0=+$('b1s').value,g=+$('b1g').value,v=+$('b1v').value*1e4,c=+$('b1c').value*1e4,w=+$('b1w').value*1e4,f=+$('b1f').value*1e4,pr=$('b1p').checked;
 $('b1gv').textContent=g+'%';var p=Math.max(0,Math.min(1,p0/100*g/100)),fv=pr?v:f,win=w-c-v,lose=fv-c-v,ev=p*win+(1-p)*lose,ml=lose<0?-lose:0,be=win>lose?(-lose)/(win-lose)*100:NaN;
 $('b1o1').innerHTML=box('실제 성공 확률',(p*100).toFixed(1)+'%','공식 '+p0+'% × 게이지 '+g+'%')+box('성공하면',bp(win),'시도 전 대비','up')+box('실패하면',bp(lose),(100-p*100).toFixed(0)+'% 확률','dn');
 $('b1o2').innerHTML=box('확률 가중 기대값',bp(ev))+box('최대 손실',bp(ml),'','dn')+box('손익분기 확률',isNaN(be)?'—':be.toFixed(1)+'%');}
var POL={'1':'완전 분리 매칭','2':'통합 유지 + 조작 밸런스 개선','3':'선택형 동일 장치 우선 매칭'},TXT={
 '1':'<b>공정성 체감은 좋아질 수 있지만</b> 소수 장치·상위 랭크의 대기시간이 가장 먼저 무너진다',
 '2':'<b>매칭 풀은 그대로</b> · 조작 밸런스 개선만으로 불만이 줄어드는지 만족도로 검증',
 '3':'<b>원하는 사람만 같은 장치 우선</b> · 오래 걸리면 통합으로 넓히는 선택권 → 대기시간·포기율을 가드레일로'},pol='3';
function C(){var k=+$('c5k').value/100,n=+$('c5n').value,r=+$('c5r').value,al=+$('c5a').value,pf=+$('c5f').value/100;
 $('c5kv').textContent=$('c5k').value+'%';$('c5av').textContent=al.toFixed(1)+'배';$('c5fv').textContent=$('c5f').value+'%';
 var base=n*r,kb,pad;if(pol==='1'){kb=base*k;pad=base*(1-k);}else if(pol==='2'){kb=pad=base;}else{kb=pf>0?base*k*pf:base;pad=pf>0?base*(1-k)*pf:base;}
 var kx=kb>0?base/kb:Infinity,px=pad>0?base/pad:Infinity,fb=pol==='3'&&Math.max(kx,px)>al;if(pol==='3'){kx=Math.min(kx,al);px=Math.min(px,al);}
 var worst=Math.max(kx,px),risk=fb?'주의 · 통합 확대':(worst>al?'높음':(worst>al*0.7?'주의':'낮음'));
 $('c5h').innerHTML=pol+'안 · '+POL[pol]+' """ + B_SIM.replace('"', '\\"') + """';
 var o=pol==='3'?'(우선 선택)':'';
 $('c5o').innerHTML=box('키보드 유저'+o+'의 상대 풀',Math.round(kb).toLocaleString('ko-KR')+'명','대기 ≈ 통합의 '+kx.toFixed(1)+'배')+
  box('패드 유저'+o+'의 상대 풀',Math.round(pad).toLocaleString('ko-KR')+'명','대기 ≈ 통합의 '+px.toFixed(1)+'배')+box('대기시간 위험',risk,'허용 '+al.toFixed(1)+'배 기준',risk==='높음'?'dn':'');
 $('c5t').innerHTML=TXT[pol];$('c5s').textContent=(pol==='3'?'3안은 허용 배수에 닿으면 통합으로 넓히므로 대기 상한 = 허용 배수 · 우선을 고르지 않은 유저는 통합 그대로 · ':'')+'실제 매칭 알고리즘이 아닌 단순 모델 · 대기시간은 실제 초가 아니라 통합 매칭 대비 상대 배수 (풀 크기에 반비례 가정)';}
function mount(){document.querySelectorAll('.fc-live').forEach(function(el){var a=document.querySelector('.fc-anchor[data-k="'+el.dataset.k+'"]');
  var row=a&&a.closest('.sx-row');if(row){row.replaceWith(el);el.hidden=false;}});
 ['a1v','a1m','a1k'].forEach(function(i){$(i).addEventListener('input',A);});
 ['b1s','b1g','b1v','b1c','b1w','b1f','b1p'].forEach(function(i){$(i).addEventListener('input',B);$(i).addEventListener('change',B);});
 ['c5k','c5n','c5r','c5a','c5f'].forEach(function(i){$(i).addEventListener('input',C);$(i).addEventListener('change',C);});
 $('c5p').querySelectorAll('button').forEach(function(b){b.addEventListener('click',function(){$('c5p').querySelectorAll('button').forEach(function(x){x.setAttribute('aria-pressed','false');});
  b.setAttribute('aria-pressed','true');pol=b.dataset.k;C();});});
 A();B();C();}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount);else mount();
})();</script>"""
    return PAGE_EXTRA_CSS + a1 + b1 + c5 + js
