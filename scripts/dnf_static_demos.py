"""정적 보고서(GitHub Pages)용 던파 시뮬레이터 — 현행 vs B 진척 게이지(제안) vs 천장(비교) (서버 없이 브라우저에서 조작).

Streamlit 입력 칸 첫머리의 <div class="fc-anchor" data-k="d1">가 든 행(.sx-row)을 아래 조작판으로 바꾼다.
계산식·난수열(mulberry32, 시드 20261123)·이용자 수(2,000명)는 gamepulse/sim/dnf_sim.py 와 같다.
"""

from __future__ import annotations

from fc_static_demos import PAGE_EXTRA_CSS

B_SIM = '<span class="gp-badge k-sim">가정 시뮬레이션</span>'


def demos() -> str:
    hint = '<div class="hint">값을 바꾸면 바로 다시 계산</div>'
    panel = ('<div class="fc-live" data-k="d1" hidden><div class="ctl">'
             '<label>주간 클리어 누적 횟수 <b id="dnv"></b><input type="range" id="dn" min="10" max="200" step="5" value="50"></label>'
             '<label>기대 이상 결과 확률 (% · 가정) <b id="dpv"></b><input type="range" id="dp" min="1" max="30" value="5"></label>'
             '<label>기대 이상 결과의 보상 배율 (× · 가정) <b id="dmv"></b><input type="range" id="dm" min="2" max="20" value="10"></label>'
             '<label>게이지 칸 수 K: 기대 미만 클리어 K번마다 1회 하한 보장 (0 = 없음) <b id="dkv"></b><input type="range" id="dk" min="0" max="50" step="5" value="10"></label>'
             '<label style="flex-direction:row;align-items:center;gap:.4rem"><input type="checkbox" id="dneu">공급 중립 (고배율 보상 크기를 줄여 평균을 현행과 같게)</label></div>'
             f'<div id="dout"></div>{hint}</div>')
    js = """<script>(function(){
function $(i){return document.getElementById(i);}
function rng(a){return function(){a|=0;a=a+0x6D2B79F5|0;var t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}
function st(xs){var s=xs.slice().sort(function(a,b){return a-b;}),n=s.length,m=s.reduce(function(a,b){return a+b;},0)/n,
 v=s.reduce(function(a,x){return a+(x-m)*(x-m);},0)/n;return {mean:m,sd:Math.sqrt(v),p10:s[Math.floor(n*0.1)],min:s[0]};}
function sum(x){return x.reduce(function(a,b){return a+b;},0);}
function sim(N,p,M,K,neu){var r=rng(20261123),P=2000,E=(1-p)+p*M,A=[],BH=[],BG=[],CH=[];
 for(var i=0;i<P;i++){var a=0,hb=0,gb=0,hc=0,g=0,miss=0;
  for(var j=0;j<N;j++){var hit=r()<p;a+=hit?M:1;
   if(hit)hb++;else{g++;if(K&&g>=K){gb++;g=0;}}
   var forced=(!hit)&&K&&miss>=K;if(hit||forced){hc++;miss=0;}else miss++;}
  A.push(a);BH.push(hb);BG.push(gb);CH.push(hc);}
 var SA=st(A),totA=sum(A),base=N*P,sb=1,sc=1;
 if(neu){var hs=sum(BH),gs=sum(BG),cs=sum(CH);if(hs)sb=Math.max(0,(totA-base-gs*(E-1))/(hs*(M-1)));if(cs)sc=Math.max(0,(totA-base)/(cs*(M-1)));}
 var B=BH.map(function(h,k){return N+h*(M-1)*sb+BG[k]*(E-1);}),C=CH.map(function(h){return N+h*(M-1)*sc;});
 var SB=st(B),SC=st(C),g=SA.mean;function z(v){return Math.abs(v)<0.05?0:v;}function rc(x){return x.filter(function(v){return v>=g-1e-9;}).length/P*100;}
 return {A:SA,B:SB,C:SC,sb:z((SB.mean/SA.mean-1)*100),sc:z((SC.mean/SA.mean-1)*100),jb:1+(M-1)*sb,jc:1+(M-1)*sc,M:M,ra:rc(A),rb:rc(B),rc:rc(C)};}
function f(x){return x.toLocaleString('ko-KR',{minimumFractionDigits:1,maximumFractionDigits:1});}
function cell(a,v,low){var d=v-a,c=(low?d<0:d>0)?'up':(Math.abs(d)>1e-9?'dn':'');return '<td class="'+c+'"><b>'+f(v)+'</b> <small>('+(d>=0?'+':'')+f(d)+')</small></td>';}
function row(n,a,b,c,low){return '<tr><td>'+n+'</td><td>'+f(a)+'</td>'+cell(a,b,low)+cell(a,c,low)+'</tr>';}
function sup(v){return '<b class="'+(Math.abs(v)>5?'dn':'up')+'">'+(v>=0?'+':'')+v.toFixed(1)+'%</b>';}
function ins(r){var A=r.A,B=r.B;if(B.p10<A.p10)return '<b>B도 하위 10%가 줄어듦</b> · 이 설정은 개선안으로 쓰지 않는다';
 var m='<b>B 불운 진척 게이지</b> · 하위 10% '+A.p10.toFixed(1)+' → '+B.p10.toFixed(1)+' · 공급 '+(r.sb>=0?'+':'')+r.sb.toFixed(1)+'% · 고배율 ×'+r.jb.toFixed(1)+' '+
  (Math.abs(r.sb)<=5?'→ 가드레일(±5%) 안에서 운이 나쁜 구간만 보완':'→ 공급이 가드레일(±5%)을 넘음: K를 늘리거나 공급 중립을 켠다');
 if(Math.abs(r.sc)>5)m+='<br><b>천장 (반례)</b> · 공급 '+(r.sc>=0?'+':'')+r.sc.toFixed(1)+'% → 재화 공급 과열';
 else if(r.jc<r.M*0.8)m+='<br><b>천장 (반례)</b> · 공급을 맞추려면 고배율이 ×'+r.M+' → ×'+r.jc.toFixed(1)+'로 줄어 확률 보상의 설렘이 크게 약해짐';
 return m;}
function D(){var N=+$('dn').value,p=+$('dp').value/100,M=+$('dm').value,K=+$('dk').value,neu=$('dneu').checked;
 $('dnv').textContent=N+'회';$('dpv').textContent=$('dp').value+'%';$('dmv').textContent='×'+M;$('dkv').textContent=K?K+'칸':'없음';
 var r=sim(N,p,M,K,neu),A=r.A,B=r.B,C=r.C;
 $('dout').innerHTML='<div class="fc-demo"><h4>현행 vs B 불운 진척 게이지 (제안) vs 천장 (비교) """ + B_SIM.replace("'", "\\'") + """</h4><div class="fc-cmp"><table>'+
  '<tr><th>지표 (이용자 2,000명 · 가정)</th><th>현행</th><th>B 불운 진척 게이지</th><th>천장 (비교)</th></tr>'+
  row('하위 10% 누적 보상',A.p10,B.p10,C.p10)+row('최저 누적 보상',A.min,B.min,C.min)+row('평균 총보상',A.mean,B.mean,C.mean)+row('보상 편차 (표준편차)',A.sd,B.sd,C.sd,true)+row('현행 평균 이상 도달 비율 (%)',r.ra,r.rb,r.rc)+
  '<tr><td>보상 재화 공급량 변화</td><td>—</td><td>'+sup(r.sb)+'</td><td>'+sup(r.sc)+'</td></tr>'+
  '<tr><td>고배율 보상 크기 (×)</td><td>'+M+'</td><td><b>'+r.jb.toFixed(1)+'</b></td><td><b>'+r.jc.toFixed(1)+'</b></td></tr></table></div>'+
  '<div class="fc-act">'+ins(r)+'</div>'+
  '<div class="src">가정 시뮬레이션 · 확률·배율·K는 실제 던파 수치가 아님 · B 진척 게이지: 기대 미만 클리어가 K번 쌓이면 그 클리어 보상을 기대 배율 하한(1회 기대 보상)까지 보장 · 천장(비교): K회 연속 기대 미만이면 다음 1회 고배율 확정 · 공급 중립은 고배율 보상 크기만 조정 · 같은 난수열(시드 고정)</div></div>';}
function mount(){var el=document.querySelector('.fc-live[data-k="d1"]'),a=document.querySelector('.fc-anchor[data-k="d1"]'),row=a&&a.closest('.sx-row');
 if(el&&row){row.replaceWith(el);el.hidden=false;}
 ['dn','dp','dm','dk'].forEach(function(i){$(i).addEventListener('input',D);});$('dneu').addEventListener('change',D);D();}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount);else mount();
})();</script>"""
    return PAGE_EXTRA_CSS + panel + js
