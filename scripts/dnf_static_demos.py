"""정적 보고서(GitHub Pages)용 던파 시뮬레이터 — 현행 랜덤 vs 누적 보장 병행 (서버 없이 브라우저에서 조작).

Streamlit 입력 칸 첫머리의 <div class="fc-anchor" data-k="d1">가 든 행(.sx-row)을 아래 조작판으로 바꾼다.
계산식·난수열(mulberry32, 시드 20261123)·이용자 수(2,000명)는 gamepulse/sim/dnf_sim.py 와 같다.
"""

from __future__ import annotations

from fc_static_demos import PAGE_EXTRA_CSS

B_SIM = '<span class="gp-badge k-sim">가정 시뮬레이션</span>'


def demos() -> str:
    hint = '<div class="hint">값을 바꾸면 바로 다시 계산</div>'
    panel = ('<div class="fc-live" data-k="d1" hidden><div class="ctl">'
             '<label>클리어 횟수 <b id="dnv"></b><input type="range" id="dn" min="10" max="200" step="5" value="50"></label>'
             '<label>고배율 확률 (% · 가정) <b id="dpv"></b><input type="range" id="dp" min="1" max="30" value="5"></label>'
             '<label>고배율 보상 배율 (× · 가정) <b id="dmv"></b><input type="range" id="dm" min="2" max="20" value="10"></label>'
             '<label>누적 보장 조건: K회 연속 미당첨 시 확정 (0 = 없음) <b id="dkv"></b><input type="range" id="dk" min="0" max="100" step="5" value="30"></label>'
             '<label style="flex-direction:row;align-items:center;gap:.4rem"><input type="checkbox" id="dneu" checked>공급 중립 (평균 총보상을 현행과 같게 조정)</label></div>'
             f'<div id="dout"></div>{hint}</div>')
    js = """<script>(function(){
function $(i){return document.getElementById(i);}
function rng(a){return function(){a|=0;a=a+0x6D2B79F5|0;var t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
function st(xs){var s=xs.slice().sort(function(a,b){return a-b;}),n=s.length,m=s.reduce(function(a,b){return a+b;},0)/n,
 v=s.reduce(function(a,x){return a+(x-m)*(x-m);},0)/n;return {mean:m,sd:Math.sqrt(v),p10:s[Math.floor(n*0.1)],min:s[0]};}
function sim(N,p,M,K,neu){var r=rng(20261123),A=[],B=[],P=2000;
 for(var i=0;i<P;i++){var a=0,b=0,miss=0;for(var j=0;j<N;j++){var u=r(),hit=u<p;a+=hit?M:1;if(!hit&&K&&miss>=K)hit=true;b+=hit?M:1;miss=hit?0:miss+1;}A.push(a);B.push(b);}
 var SA=st(A),bm=B.reduce(function(x,y){return x+y;},0)/P,sc=neu?SA.mean/bm:1;B=B.map(function(x){return x*sc;});var SB=st(B),g=SA.mean;
 var sup0=(SB.mean/SA.mean-1)*100;return {A:SA,B:SB,ra:A.filter(function(x){return x>=g;}).length/P*100,rb:B.filter(function(x){return x>=g;}).length/P*100,sup:(Math.abs(sup0)<0.05?0:sup0),epc:(1-p)+p*M};}
function f(x){return x.toLocaleString('ko-KR',{minimumFractionDigits:1,maximumFractionDigits:1});}
function row(n,a,b,low){var d=b-a,c=(low?d<0:d>0)?'up':(d?'dn':'');return '<tr><td>'+n+'</td><td>'+f(a)+'</td><td><b>'+f(b)+'</b></td><td class="'+c+'">'+(d>=0?'+':'')+f(d)+'</td></tr>';}
function D(){var N=+$('dn').value,p=+$('dp').value/100,M=+$('dm').value,K=+$('dk').value,neu=$('dneu').checked;
 $('dnv').textContent=N+'회';$('dpv').textContent=$('dp').value+'%';$('dmv').textContent='×'+M;$('dkv').textContent=K?K+'회':'없음';
 var r=sim(N,p,M,K,neu),A=r.A,B=r.B;
 $('dout').innerHTML='<div class="fc-demo"><h4>현행 랜덤 vs 누적 보장 병행 """ + B_SIM.replace("'", "\\'") + """</h4><div class="fc-cmp"><table>'+
  '<tr><th>지표 (이용자 2,000명 가정)</th><th>현행 랜덤</th><th>보장 병행</th><th>차이</th></tr>'+
  row('평균 총보상',A.mean,B.mean)+row('보상 편차 (표준편차)',A.sd,B.sd,true)+row('하위 10% 누적 보상',A.p10,B.p10)+row('최저 누적 보상',A.min,B.min)+row('목표 도달 비율 (%)',r.ra,r.rb)+'</table></div>'+
  '<div class="fc-m two"><div><small>보상 재화 공급량 변화</small><b class="'+(r.sup>5?'dn':'up')+'">'+(r.sup>=0?'+':'')+r.sup.toFixed(1)+'%</b><em>가드레일 ±5% (제안값)</em></div>'+
  '<div><small>1회 기대 보상 (현행)</small><b>'+r.epc.toFixed(2)+'</b><em>기본 보상 = 1</em></div></div>'+
  '<div class="fc-act">'+(B.p10<A.p10?'<b>천장만으로는 부족</b> · 공급 중립이면 하위 10%가 오히려 줄어든다 → 클리어마다 확정 진척을 주는 <b>C-1</b>을 대표안으로':
   (r.sup>5?'<b>공급 과열 주의</b> · 재화 공급이 가드레일(+5%)을 넘는다 → 공급 중립 조정 또는 K를 늘린다':'<b>불운 구간 축소</b> · 하위 10%·최저 보상이 오르고 편차가 줄어든다 · 공급 변화는 가드레일 안'))+'</div>'+
  '<div class="src">이 시뮬레이터는 C-2 천장 방식 · 가정 기반 시뮬레이션 · 확률·배율은 실제 던파 수치가 아님 · 목표 = 현행 평균 총보상 · 같은 난수열(시드 고정)</div></div>';}
function mount(){var el=document.querySelector('.fc-live[data-k="d1"]'),a=document.querySelector('.fc-anchor[data-k="d1"]'),row=a&&a.closest('.sx-row');
 if(el&&row){row.replaceWith(el);el.hidden=false;}
 ['dn','dp','dm','dk'].forEach(function(i){$(i).addEventListener('input',D);});$('dneu').addEventListener('change',D);D();}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount);else mount();
})();</script>"""
    return PAGE_EXTRA_CSS + panel + js
