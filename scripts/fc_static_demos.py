"""정적 보고서(GitHub Pages)용 FC 온라인 데모 2개 (A 급락 완충 대상 판정 · C 조작 최적화 실험) + 갤러리 보강 — 서버 없이 브라우저에서 조작.

Streamlit 데모 입력 칸 첫머리의 <div class="fc-anchor" data-k="…">를 찾아 그 행(.sx-row = 입력 칸 + 결과 칸)을
아래 조작판으로 바꾼다. JavaScript 가 없으면 Streamlit 기본 화면 스냅샷만 보인다. 계산식은 gamepulse/sim/fc_sim.py 와 같다.
갤러리: 정적 페이지는 #해시로 탭을 바꾸므로 갤러리 링크의 해시 이동을 막고, 넘기기·확대·닫기(Esc)를 JS 로 처리한다.
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

B_SIM = '<span class="gp-badge k-sim">가정 시뮬레이션</span>'

PAGE_EXTRA_CSS = """<style>
.fc-live .ctl{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.55rem 1rem;margin:.2rem 0 .8rem}
.fc-live label{display:flex;flex-direction:column;gap:.25rem;font-size:.9rem;color:#1E293B}
.fc-live label b{color:#6D28D9}
.fc-live input[type=number],.fc-live select{padding:.45rem .6rem;border:1px solid #CBD5E1;border-radius:8px;font-size:.95rem;background:#F8FAFC;font-family:inherit}
.fc-live input[type=range]{accent-color:#15803D}
.fc-live .seg{display:flex;flex-wrap:wrap;gap:.35rem;grid-column:1/-1}
.fc-live .seg button{border:1px solid #CBD5E1;background:#fff;border-radius:999px;padding:.3rem .8rem;font-size:.9rem;cursor:pointer;font-family:inherit}
.fc-live .seg button[aria-pressed=true]{background:#15803D;border-color:#15803D;color:#fff}
.fc-live .hint{font-size:.8rem;color:#475569;margin-top:.4rem}
@media(max-width:700px){.fc-live .ctl{grid-template-columns:1fr}}
body.fc-noscroll{overflow:hidden}
</style>"""


def demos(root: Path) -> str:
    d = json.loads((root / "data" / "fconline" / "fc.json").read_text(encoding="utf-8"))
    pols = {p["key"]: {"fair": p["fair"], "ops": p["ops"]} for p in d["c_policies"]}
    ad = d["a_demo"]
    hint = '<div class="hint">값을 바꾸면 바로 다시 계산</div>'
    sl = "".join(
        f'<label>{escape(nm)} 7일 하락률 (7일 전 {pk:g}억) <b id="ap{i}v"></b><input type="range" id="ap{i}" min="0" max="90" value="{round((1 - now / pk) * 100)}"></label>'
        f'<label style="flex-direction:row;align-items:center;gap:.4rem"><input type="checkbox" id="ah{i}" checked>{escape(nm)} · 급락 전부터 보유</label>'
        for i, (nm, pk, now) in enumerate(ad["players"]))
    a1 = ('<div class="fc-live" data-k="a1" hidden><div class="ctl">'
          f'<label>시장 전체 7일 하락률 (% · 가정) <b id="amkv"></b><input type="range" id="amk" min="0" max="80" value="{ad["market"]}"></label>'
          '<label>대상 기준: 보유 선수 7일 하락률 (% · 파일럿 검토용 가정 40~50) <b id="athv"></b><input type="range" id="ath" min="40" max="50" value="45"></label>'
          f'{sl}</div><div id="aout"></div>{hint}</div>')
    c5 = ('<div class="fc-live" data-k="c5" hidden><div class="ctl"><div class="seg" id="c5p">'
          '<button type="button" data-k="c1" aria-pressed="true">기능 1 · 대각선·연속 입력 성공률</button>'
          '<button type="button" data-k="c2" aria-pressed="false">기능 1 · 입력-패스 방향 일치율</button></div>'
          '<label>키보드 현행 (% · 가정) <b id="c5kv"></b><input type="range" id="c5k" min="40" max="100" value="78"></label>'
          '<label>패드 현행 (% · 가정) <b id="c5pv"></b><input type="range" id="c5pd" min="40" max="100" value="86"></label>'
          '<label>실험 후 키보드 변화 (+%p · 가정) <b id="c5uv"></b><input type="range" id="c5u" min="0" max="15" value="4"></label>'
          '<label>실험 후 패드 변화 (%p · 가정) <b id="c5cv"></b><input type="range" id="c5c" min="-5" max="5" value="0"></label>'
          '<label>매칭 포기율 변화 (%p · 가정) <b id="c5qv"></b><input type="range" id="c5q" min="-1" max="2" step="0.1" value="0"></label></div>'
          '<div id="c5o"></div>' f'{hint}</div>')
    data = json.dumps({"PO": pols, "PL": ad["players"]}, ensure_ascii=False)
    js = """<script>(function(){var D=""" + data + """,PO=D.PO,PL=D.PL;
function $(i){return document.getElementById(i);}
function bp(x){x=Math.round(x);var s=x<0?'−':'';x=Math.abs(x);var jo=Math.floor(x/1e12),eok=Math.floor((x%1e12)/1e8),man=Math.floor((x%1e8)/1e4);
 var p=[];if(jo)p.push(jo.toLocaleString('ko-KR')+'조');if(eok)p.push(eok.toLocaleString('ko-KR')+'억');if(man)p.push(man.toLocaleString('ko-KR')+'만');return s+(p.join(' ')||x.toLocaleString('ko-KR'))+' BP';}
function e8(v){return bp(v*1e8);}
function esc(t){return String(t).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function A(){var mk=+$('amk').value/100,th=+$('ath').value/100;$('amkv').textContent=$('amk').value+'%';$('athv').textContent=$('ath').value+'%';
 var rows=[],mt=0,ot=0,hp=0,hl=0,hm=0,nh=0;PL.forEach(function(p,i){var dr=+$('ap'+i).value/100;$('ap'+i+'v').textContent=$('ap'+i).value+'%';
  var peak=p[1],now=peak*(1-dr),loss=Math.max(0,peak-now),m=Math.min(loss,peak*mk),o=loss-m,h=$('ah'+i).checked;
  rows.push({i:i,loss:loss,m:m,o:o});mt+=m;ot+=o;if(h){nh++;hp+=peak;hl+=loss;hm+=m;}});
 var lt=mt+ot,mx=Math.max.apply(null,rows.map(function(r){return r.loss;}))||1,drop=hp>0?hl/hp*100:0,ms=hl>0?hm/hl*100:0,ok=hp>0&&drop>=th*100;
 var bars=rows.map(function(r){var sh=lt>0?r.loss/lt*100:0;return '<div class="bar"><span>'+esc(PL[r.i][0])+'</span><div class="t"><i class="mk" style="width:'+(r.m/mx*100).toFixed(1)+'%"></i><i class="own" style="width:'+(r.o/mx*100).toFixed(1)+'%"></i></div><em>'+sh.toFixed(0)+'%</em></div>';}).join('');
 var v=ok?('<b>대상</b> · 급락 전 보유 선수 하락률 '+drop.toFixed(0)+'% ≥ 기준 '+(th*100).toFixed(0)+'% → 공식경기 단계 미션 + 비거래성 소규모 보상 제안'):
  ('<b>대상 아님</b> · 급락 전 보유 선수 하락률 '+drop.toFixed(0)+'% &lt; 기준 '+(th*100).toFixed(0)+'% → 변동률 비교 정보만 제공');
 var why=ms>=50?"시장 전체 하락이 대부분 → '내 선수 문제가 아니다'를 먼저 안내":'특정 선수 하락이 큼 → 시장 대비 개별 하락을 구분해 안내';
 $('aout').innerHTML='<div class="fc-demo"><h4>급락 완충 대상 판정 <span class="gp-badge k-sim">가정 시뮬레이션</span></h4><div class="fc-m">'+
  '<div><small>내 구단 (급락 전 보유 · 7일)</small><b class="dn">−'+drop.toFixed(0)+'%</b><em>보유 선수 '+nh+'명 기준</em></div>'+
  '<div><small>시장 전체 (7일)</small><b>−'+(mk*100).toFixed(0)+'%</b><em>차이 '+((drop-mk*100)>=0?'+':'')+(drop-mk*100).toFixed(0)+'%p</em></div>'+
  '<div><small>하락 구성 · 시장 요인</small><b>'+ms.toFixed(0)+'%</b><em>나머지 = 개별 요인</em></div></div>'+
  '<div class="fc-bars"><div class="lg"><i class="mk"></i>시장 요인 <i class="own"></i>개별 요인 · 막대 = 선수별 하락액</div>'+bars+'</div>'+
  '<div class="fc-act '+(ok?'rec':'')+'">'+v+'</div><div class="fc-act">'+why+'</div>'+
  '<div class="src">가상 선수 · 모든 값은 가정 · 대상 기준 40~50%는 확정 기준이 아닌 파일럿 검토용 · 급락 직전 매수 선수는 제외 · 손실 비례 BP 보상 없음 · 계정당 지급 횟수 제한</div></div>';}
var EXP={c1:['입력 성공률',78,86],c2:['방향 일치율',84,88]},ex='c1',VER={
 '확대':'격차가 목표만큼 줄고 패드·매칭 지표 악화 없음 → 적용 범위 확대',
 '수정':'격차는 줄었지만 목표(30%) 미달 → 판정 조건 수정 후 재실험',
 '중단':'격차가 줄지 않거나 패드·매칭 지표 악화 → 중단 · 의견은 수비 AI·밸런스 과제로'};
function C(){var kb=+$('c5k').value,pd=+$('c5pd').value,up=+$('c5u').value,pc=+$('c5c').value,qc=+$('c5q').value;
 $('c5kv').textContent=kb+'%';$('c5pv').textContent=pd+'%';$('c5uv').textContent='+'+up+'%p';$('c5cv').textContent=(pc>0?'+':'')+pc+'%p';$('c5qv').textContent=(qc>0?'+':'')+qc.toFixed(1)+'%p';
 var g0=pd-kb,kb1=Math.min(100,kb+up),pd1=Math.max(0,Math.min(100,pd+pc)),g1=pd1-kb1,cut=g0>0?(g0-g1)/g0*100:0,guard=pc>=-1&&qc<=0.5,
  v=(cut>=30&&guard)?'확대':((cut<=0||!guard)?'중단':'수정');
 function row(n,a,b,c){return '<tr class="'+(c||'')+'"><td>'+n+'</td><td>'+a+'</td><td><b>'+b+'</b></td></tr>';}
 $('c5o').innerHTML='<div class="fc-demo c"><h4>실험 판정 · '+EXP[ex][0]+' ' + '<span class="gp-badge k-sim">가정 시뮬레이션</span></h4><div class="fc-cmp"><table><tr><th>구분</th><th>현행 (대조군)</th><th>실험군</th></tr>'+
  row('키보드',kb+'%',kb1.toFixed(0)+'%')+row('패드',pd+'%',pd1.toFixed(0)+'%')+row('격차 (패드 − 키보드)',g0.toFixed(0)+'%p',g1.toFixed(0)+'%p','on')+
  '</table></div><div class="fc-m two"><div><small>격차 축소율 (목표 30% · 예시)</small><b class="'+(cut>0?'up':'dn')+'">'+cut.toFixed(0)+'%</b></div>'+
  '<div><small>가드레일 · 패드 −1%p · 포기율 +0.5%p</small><b class="'+(guard?'up':'dn')+'">'+(guard?'통과':'위반')+'</b></div></div>'+
  '<div class="fc-act '+(v==='확대'?'rec':'')+'"><b>판정: '+v+'</b> · '+VER[v]+'</div>'+
  '<div class="src">모든 값은 가정 · 실제 유저 데이터 아님 · 매칭은 통합 그대로 (분리 매칭은 최종안에서 제외)</div></div>';}
function mount(){document.querySelectorAll('.fc-live').forEach(function(el){var a=document.querySelector('.fc-anchor[data-k="'+el.dataset.k+'"]');
  var row=a&&a.closest('.sx-row');if(row){row.replaceWith(el);el.hidden=false;}});
 ['amk','ath'].concat(PL.map(function(_,i){return 'ap'+i;})).forEach(function(i){$(i).addEventListener('input',A);});
 PL.forEach(function(_,i){$('ah'+i).addEventListener('change',A);});
 ['c5k','c5pd','c5u','c5c','c5q'].forEach(function(i){$(i).addEventListener('input',C);});
 $('c5p').querySelectorAll('button').forEach(function(b){b.addEventListener('click',function(){$('c5p').querySelectorAll('button').forEach(function(x){x.setAttribute('aria-pressed','false');});
  b.setAttribute('aria-pressed','true');ex=b.dataset.k;$('c5k').value=EXP[ex][1];$('c5pd').value=EXP[ex][2];C();});});
 A();C();}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount);else mount();
})();</script>"""
    return PAGE_EXTRA_CSS + a1 + c5 + js
