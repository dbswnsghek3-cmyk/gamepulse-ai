"""정적 보고서(GitHub Pages)용 FC 온라인 데모 2개 (A 구단 가치 분석·재건 · C 정책 비교) + 갤러리 보강 — 서버 없이 브라우저에서 조작.

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
        f'<label>{escape(nm)} 하락률 (고점 {pk:g}억) <b id="ap{i}v"></b><input type="range" id="ap{i}" min="0" max="90" value="{round((1 - now / pk) * 100)}"></label>'
        for i, (nm, pk, now) in enumerate(ad["players"]))
    a1 = ('<div class="fc-live" data-k="a1" hidden><div class="ctl">'
          f'<label>시장 전체 하락률 (% · 가정) <b id="amkv"></b><input type="range" id="amk" min="0" max="80" value="{ad["market"]}"></label>{sl}'
          f'<label>보유 BP (억 · 가정)<input type="number" id="ahold" value="{ad["hold"]}" min="0" step="0.1"></label>'
          f'<label>판매 수수료율 (% · 가정) <b id="afeev"></b><input type="range" id="afee" min="0" max="60" value="{ad["fee"]}"></label></div>'
          f'<div id="aout"></div>{hint}</div>')
    c5 = ('<div class="fc-live" data-k="c5" hidden><div class="ctl"><div class="seg" id="c5p">'
          '<button type="button" data-k="1" aria-pressed="false">1안 · 완전 분리 매칭</button>'
          '<button type="button" data-k="2" aria-pressed="false">2안 · 선택형 우선 매칭</button>'
          '<button type="button" data-k="3" aria-pressed="true">3안 · 통합 유지 + 입력 판정 개선 (권고)</button></div>'
          '<label>키보드 이용 비중 (%) · 기본값 54.6 = 공식 상위 1만 1ON1 <b id="c5kv">54.6%</b><input type="range" id="c5k" min="5" max="95" step="0.1" value="54.6"></label>'
          '<label>2안 · 동일 장치 우선 선택 비율 (% · 가정) <b id="c5fv">40%</b><input type="range" id="c5f" min="0" max="100" value="40"></label></div>'
          f'<div class="fc-demo c"><h4>정책 비교 {B_SIM}</h4><div class="fc-cmp"><table id="c5t"></table></div><div class="fc-act" id="c5m"></div>'
          '<div class="fc-act rec"><b>최종 권고 3안 고정</b> · 1·2안은 제외한 대안 (비교용)</div>'
          '<div class="src">이용자 수·대기시간이 아닌 비율 모델 · 위험 구분선(40%·70%)은 모델용</div></div>'
          f'{hint}</div>')
    data = json.dumps({"PO": pols, "PL": ad["players"]}, ensure_ascii=False)
    js = """<script>(function(){var D=""" + data + """,PO=D.PO,PL=D.PL;
function $(i){return document.getElementById(i);}
function bp(x){x=Math.round(x);var s=x<0?'−':'';x=Math.abs(x);var jo=Math.floor(x/1e12),eok=Math.floor((x%1e12)/1e8),man=Math.floor((x%1e8)/1e4);
 var p=[];if(jo)p.push(jo.toLocaleString('ko-KR')+'조');if(eok)p.push(eok.toLocaleString('ko-KR')+'억');if(man)p.push(man.toLocaleString('ko-KR')+'만');return s+(p.join(' ')||x.toLocaleString('ko-KR'))+' BP';}
function e8(v){return bp(v*1e8);}
function esc(t){return String(t).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function A(){var mk=+$('amk').value/100,hold=Math.max(0,+$('ahold').value||0),fee=+$('afee').value/100;$('amkv').textContent=$('amk').value+'%';$('afeev').textContent=$('afee').value+'%';
 var rows=[],pk=0,nw=0,mt=0,ot=0;PL.forEach(function(p,i){var dr=+$('ap'+i).value/100;$('ap'+i+'v').textContent=$('ap'+i).value+'%';
  var peak=p[1],now=peak*(1-dr),loss=Math.max(0,peak-now),m=Math.min(loss,peak*mk),o=loss-m;rows.push({i:i,peak:peak,now:now,loss:loss,m:m,o:o,sw:o>m});pk+=peak;nw+=now;mt+=m;ot+=o;});
 var lt=mt+ot,sw=rows.filter(function(r){return r.sw;}),sale=sw.reduce(function(a,r){return a+r.now;},0)*(1-fee),bud=hold+sale,tg=sw.reduce(function(a,r){return a+r.peak;},0),gap=Math.max(0,tg-bud);
 var drop=pk>0?lt/pk:0,rec=drop<1?drop/(1-drop)*100:Infinity,cov=tg>0?bud/tg*100:100,mx=Math.max.apply(null,rows.map(function(r){return r.loss;}))||1;
 var bars=rows.map(function(r){var sh=lt>0?r.loss/lt*100:0;return '<div class="bar"><span>'+esc(PL[r.i][0])+'</span><div class="t"><i class="mk" style="width:'+(r.m/mx*100).toFixed(1)+'%"></i><i class="own" style="width:'+(r.o/mx*100).toFixed(1)+'%"></i></div><em class="'+(r.sw?'sw':'')+'">'+sh.toFixed(0)+'% · '+(r.sw?'교체 검토':'유지')+'</em></div>';}).join('');
 $('aout').innerHTML='<div class="fc-demo"><h4>구단 가치 분석·재건 """ + B_SIM.replace("'", "\\'") + """</h4><div class="fc-m">'+
  '<div><small>구단 가치</small><b>'+e8(nw)+'</b><em class="dn">−'+(drop*100).toFixed(0)+'% · 고점 '+e8(pk)+'</em></div>'+
  '<div><small>시장 요인 · 개별 요인</small><b>'+(lt?mt/lt*100:0).toFixed(0)+'% · '+(lt?ot/lt*100:0).toFixed(0)+'%</b><em>하락분 구성</em></div>'+
  '<div><small>고점 회복에 필요한 상승</small><b class="up">+'+rec.toFixed(0)+'%</b><em>시세 회복은 보장 불가</em></div></div>'+
  '<div class="fc-bars"><div class="lg"><i class="mk"></i>시장 요인 <i class="own"></i>개별 요인 · 막대 = 선수별 하락액</div>'+bars+'</div>'+
  '<div class="fc-m two"><div><small>① 현재 스쿼드 유지</small><b>'+e8(nw)+'</b><em>지출 0 · 경기력 그대로</em></div>'+
  '<div><small>② 교체 검토 '+sw.length+'명 재편</small><b>예산 '+e8(bud)+'</b><em>보유 BP + 판매 수익 · 고점의 '+cov.toFixed(0)+'%</em></div></div>'+
  '<ol class="fc-path"><li><b>진단</b> 개별 하락 '+sw.length+'명 · 시장 하락 '+(rows.length-sw.length)+'명</li><li><b>유지</b> 시장과 함께 내린 선수</li>'+
  '<li><b>재편</b> 교체 검토 선수 판매 → 재편 예산 '+e8(bud)+'</li><li><b>이벤트 연계</b> 남은 목표 '+e8(gap)+' → 이벤트·패스 보상 목표 (BP 지급 아님)</li></ol>'+
  '<div class="src">가상 선수 · 모든 값은 가정 · 실제 시세·수수료 아님</div></div>';}
var NAME={'1':'완전 분리 매칭','2':'선택형 우선 매칭','3':'통합 유지 + 입력 판정 개선'},MSG={
 '1':'공정성 체감은 좋아질 수 있지만 상대 풀이 장치 비중만큼 줄어든다',
 '2':'선택한 사람만 같은 장치를 먼저 찾고, 못 찾으면 통합으로 넓힌다 · 규칙이 복잡해진다',
 '3':'상대 풀은 그대로 · C-1·C-2 판정 개선 효과를 성공률·불일치율로 검증한다'},pol='3';
function C(){var k=+$('c5k').value/100,s=+$('c5f').value/100;$('c5kv').textContent=(+$('c5k').value).toFixed(1)+'%';$('c5fv').textContent=$('c5f').value+'%';
 var rows='<tr><th>정책</th><th>공정성 체감</th><th>매칭 품질 · 상대 풀 (통합=100%)</th><th>풀 축소 위험</th><th>운영 리스크</th></tr>';
 ['1','2','3'].forEach(function(key){var kb,pad;if(key==='1'){kb=k*100;pad=(1-k)*100;}else if(key==='2'){if(s>0){kb=k*s*100;pad=(1-k)*s*100;}else{kb=pad=100;}}else{kb=pad=100;}
  var m=Math.min(kb,pad),risk=m<40?'높음':(m<70?'주의':'낮음');
  rows+='<tr class="'+(key===pol?'on':'')+'"><td><b>'+key+'안</b> '+NAME[key]+(key==='3'?' <em>권고</em>':'')+'</td><td>'+PO[key].fair+'</td><td>키보드 '+kb.toFixed(1)+'% · 패드 '+pad.toFixed(1)+'%</td><td class="'+(risk==='높음'?'dn':'')+'">'+risk+'</td><td>'+PO[key].ops+'</td></tr>';});
 $('c5t').innerHTML=rows;$('c5m').innerHTML='<b>'+pol+'안 선택</b> · '+MSG[pol];}
function closeZoom(){document.querySelectorAll('.fc-gal-s.zoom').forEach(function(f){f.classList.remove('zoom');});document.body.classList.remove('fc-noscroll');}
function gal(){document.addEventListener('click',function(ev){var a=ev.target.closest&&ev.target.closest('.fc-gal a');if(!a)return;ev.preventDefault();
  var fig=a.closest('.fc-gal-s'),tr=a.closest('.tr');
  if(a.hasAttribute('data-go')){var t=tr.children[+a.getAttribute('data-go')];if(t)tr.scrollTo({left:t.offsetLeft-tr.offsetLeft,behavior:'smooth'});}
  else if(a.hasAttribute('data-zoom')){if(fig.classList.contains('zoom'))closeZoom();else{closeZoom();fig.classList.add('zoom');document.body.classList.add('fc-noscroll');}}
  else if(a.hasAttribute('data-close'))closeZoom();},true);
 document.addEventListener('keydown',function(ev){if(ev.key==='Escape')closeZoom();});
 document.addEventListener('click',function(ev){var f=ev.target.classList&&ev.target.classList.contains('fc-gal-s')&&ev.target.classList.contains('zoom');if(f)closeZoom();});}
function mount(){document.querySelectorAll('.fc-live').forEach(function(el){var a=document.querySelector('.fc-anchor[data-k="'+el.dataset.k+'"]');
  var row=a&&a.closest('.sx-row');if(row){row.replaceWith(el);el.hidden=false;}});
 ['amk','ahold','afee'].concat(PL.map(function(_,i){return 'ap'+i;})).forEach(function(i){$(i).addEventListener('input',A);});
 ['c5k','c5f'].forEach(function(i){$(i).addEventListener('input',C);});
 $('c5p').querySelectorAll('button').forEach(function(b){b.addEventListener('click',function(){$('c5p').querySelectorAll('button').forEach(function(x){x.setAttribute('aria-pressed','false');});
  b.setAttribute('aria-pressed','true');pol=b.dataset.k;C();});});
 A();C();gal();}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount);else mount();
})();</script>"""
    return PAGE_EXTRA_CSS + a1 + c5 + js
