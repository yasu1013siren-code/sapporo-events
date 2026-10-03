export function tokyoDay(now=new Date()){return new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Tokyo'}).format(now)}
export function addDay(s,n){const d=new Date(s+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+n);return d.toISOString().slice(0,10)}
export function selectEvents(events,s,today=tokyoDay()){
 const dow=new Date(today+'T00:00:00Z').getUTCDay();const end=addDay(today,6-((dow+6)%7));
 return events.filter(e=>{
 if(s.area!=='all' && !(e.area===s.area || s.area==='中央区'&&e.area==='すすきの'))return false;
 if(s.kind!=='all'&&e.kind!==s.kind)return false;
 if(s.period==='unknown')return !e.start;
 if(!e.start||e.end<today)return false;
 const from=s.period==='future'?addDay(today,7):today, to=s.period==='future'?addDay(today,30):end;
 return e.start<=to&&e.end>=from;
 });
}
if(typeof document!=='undefined'){
 const $=id=>document.getElementById(id);let data=null;const ids=['store','area','period','kind'];
 const settings=()=>Object.fromEntries(ids.map(id=>[id,$(id).value]));
 try{const saved=JSON.parse(localStorage.getItem('restaurant-pro-beta')||'{}');ids.forEach(id=>{if(typeof saved[id]==='string' && (id==='store'||Array.from($(id).options).some(o=>o.value===saved[id])))$(id).value=saved[id].slice(0,80)})}catch{}
 const line=(parent,tag,text)=>{const el=document.createElement(tag);el.textContent=text;parent.append(el);return el};
 function render(){if(!data)return;const rows=selectEvents(data.events,settings());$('list').replaceChildren();$('status').textContent=`${rows.length}件 · 出力更新 ${data.generated_at} · ${data.note}`;if(!rows.length)line($('list'),'p','条件に一致する情報はありません。日時不明や地区設定も確認してください。');
 rows.forEach(e=>{const card=document.createElement('article');line(card,'h2',e.title);line(card,'p',`${e.kind} / ${e.area} / ${e.date_status}${e.prediction?' / 予定表記あり（確定は根拠確認）':''}`);line(card,'p',`${e.date_text||'日時不明'} · ${e.place||'会場不明'}`);line(card,'p','営業確認：開催・終了時刻、動線、営業時間との重なりを確認。仕込み・人員の判断は店舗で行ってください。');line(card,'small',`情報源 ${e.source} / 最終収集確認日 ${e.last_seen||'不明'} / 記事公開日 ${e.published_date||'不明'}`);try{const url=new URL(e.url);if(['https:','http:'].includes(url.protocol)){const a=line(card,'a',' 根拠を確認');a.href=url.href;a.target='_blank';a.rel='noopener noreferrer'}}catch{}$('list').append(card)});
 }
 async function load(){try{const r=await fetch('pro-events.json',{cache:'no-store'});if(!r.ok)throw Error();const next=await r.json();if(!Array.isArray(next.events)||!next.events.every(e=>e&&typeof e.title==='string'&&typeof e.url==='string'))throw Error();data=next;render()}catch{$('status').textContent=data?'取得失敗：前回表示を保持しています。更新日時を確認してください。':'取得失敗：情報を表示できません。再取得してください。'}}
 $('settings').addEventListener('submit',e=>{e.preventDefault();try{localStorage.setItem('restaurant-pro-beta',JSON.stringify(settings()));render();$('status').textContent+=' · 設定保存済み（このブラウザのみ）'}catch{$('status').textContent='設定を保存できません。現在の絞り込みは利用できます。'}});ids.forEach(id=>$(id).addEventListener('change',render));$('reload').onclick=load;
 $('digest').onclick=()=>{if(!data){$('preview').value='データ未取得。通知文は作成できません。';return}const rows=selectEvents(data.events,settings());const text=[`${$('store').value||'店舗'}向け PRO β ダイジェスト（未送信）`, `出力更新 ${data.generated_at}`, '予定・日時不明は原文確認。来客予測なし。',...rows.map(e=>`${e.title} | ${e.date_text||'日時不明'} | ${e.area} | ${e.prediction?'予定表記あり | ':''}最終収集 ${e.last_seen||'不明'} | ${e.url}`)].join('\n');$('preview').value=text;const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='pro-digest.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};load();
}
