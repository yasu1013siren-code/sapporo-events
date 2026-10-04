export const PRICE_YEN=500;
export const BUSINESSES=['居酒屋・バー','カフェ','レストラン','その他'];
export const AREAS=['すすきの周辺','大通周辺','札幌駅周辺','中央区その他','札幌市その他','札幌近郊'];
export const USEFUL=['地域・期間の絞り込み','営業メモ・お気に入り','スタッフ共有・CSV','開店・閉店情報','役立つ機能なし'];
export const WILLINGNESS=['継続したい','条件が合えば継続したい','無料なら使いたい','利用しない'];
const UUID=/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/;
const TOKEN=/^[a-f0-9]{64}$/;
const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
export function jstDay(now){return new Date(now.getTime()+9*60*60*1000).toISOString().slice(0,10)}
function plusDays(day,n){const d=new Date(day+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+n);return d.toISOString().slice(0,10)}
async function hash(key){const buf=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(key));return [...new Uint8Array(buf)].map(x=>x.toString(16).padStart(2,'0')).join('')}
async function read(request){
 if(request.method!=='POST')throw {status:405,message:'この操作は送信ボタンから行ってください。'};
 const origin=request.headers.get('origin');if(!origin||origin!==new URL(request.url).origin)throw {status:403,message:'受付ページから送信してください。'};
 if(!request.headers.get('content-type')?.startsWith('application/json'))throw {status:415,message:'送信形式を確認してください。'};
 if(Number(request.headers.get('content-length')||0)>16000)throw {status:413,message:'入力内容が長すぎます。'};
 const text=await request.text();if(new TextEncoder().encode(text).byteLength>16000)throw {status:413,message:'入力内容が長すぎます。'};
 let data;try{data=JSON.parse(text)}catch{throw {status:400,message:'送信内容を読み取れませんでした。'}}
 if(!data||typeof data!=='object'||Array.isArray(data))throw {status:400,message:'入力内容を確認してください。'};
 if(data.website)throw {status:400,message:'入力内容を確認してください。'};
 return data;
}
function identity(d){if(typeof d.id!=='string'||!UUID.test(d.id)||typeof d.key!=='string'||!TOKEN.test(d.key))throw {status:400,message:'回答リンクを確認してください。'}}
function string(d,name,max){const v=d[name];if(typeof v!=='string'||!v.trim()||v.trim().length>max)throw {status:400,message:'入力内容を確認してください。'};return v.trim()}
function number(d,name,max){const n=d[name];if(!Number.isInteger(n)||n<0||n>max)throw {status:400,message:'回数・時間は範囲内の整数で入力してください。'};return n}
function receipt(r){return {ok:true,trial_id:r.id,trial_number:'P-'+r.id.slice(0,8).toUpperCase(),start_date:r.start_date,end_date:r.end_date,price_yen:PRICE_YEN}}
function failure(e){return json({ok:false,error:e?.status?e.message:'受付に保存できませんでした。入力を残したまま、時間をおいて再送信してください。'},e?.status||503)}
async function auth(d,db){identity(d);const row=await db.prepare('SELECT id,key_hash,start_date,end_date FROM trials WHERE id = ?').bind(d.id).first();if(!row||row.key_hash!==await hash(d.key))throw {status:403,message:'回答リンクを確認してください。'};return row}
export async function signup(request,db,now=new Date()){
 try{
  if(!db)throw {status:503,message:'受付は準備中です。時間をおいてお試しください。'};
  const d=await read(request);identity(d);const store=string(d,'store',120),email=string(d,'email',254).toLowerCase();
  if(!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)||!BUSINESSES.includes(d.business)||!AREAS.includes(d.area)||d.consent!==true)throw {status:400,message:'メール・業態・地域・同意の入力を確認してください。'};
  const keyHash=await hash(d.key),start=jstDay(now),end=plusDays(start,13);
  // The same client request ID survives retry; never return another person's data.
  await db.prepare('INSERT INTO trials (id,key_hash,store,business,area,email,created_at,start_date,end_date,consent_version) VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING').bind(d.id,keyHash,store,d.business,d.area,email,now.toISOString(),start,end,'2026-10-04-v1').run();
  const r=await auth(d,db);return json(receipt(r),201);
 }catch(e){return failure(e)}
}
export async function survey(request,db,now=new Date()){
 try{
  if(!db)throw {status:503,message:'回答受付は準備中です。時間をおいてお試しください。'};
  const d=await read(request);const r=await auth(d,db);
  const uses=number(d,'uses',100),minutes=number(d,'minutes',10080);
  if(!USEFUL.includes(d.useful)||!WILLINGNESS.includes(d.willingness)||typeof d.feedback!=='string'||d.feedback.length>2000||d.consent!==true)throw {status:400,message:'回答内容・同意を確認してください。'};
  // One answer per trial. Corrections update that row instead of double-counting.
  await db.prepare('INSERT INTO answers (trial_id,uses,minutes,useful,willingness,feedback,price_yen,answered_at) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(trial_id) DO UPDATE SET uses=excluded.uses,minutes=excluded.minutes,useful=excluded.useful,willingness=excluded.willingness,feedback=excluded.feedback,price_yen=excluded.price_yen,answered_at=excluded.answered_at').bind(r.id,uses,minutes,d.useful,d.willingness,d.feedback.trim(),PRICE_YEN,now.toISOString()).run();
  return json({ok:true,trial_number:'P-'+r.id.slice(0,8).toUpperCase(),answered_at:now.toISOString(),price_yen:PRICE_YEN});
 }catch(e){return failure(e)}
}
export async function withdraw(request,db){
 try{if(!db)throw {status:503,message:'受付に接続できませんでした。'};const d=await read(request);await auth(d,db);if(d.confirm!==true)throw {status:400,message:'取り消しの確認が必要です。'};
 // D1 batch is transactional. No personal records are publicly readable.
 await db.batch([db.prepare('DELETE FROM answers WHERE trial_id = ?').bind(d.id),db.prepare('DELETE FROM trials WHERE id = ?').bind(d.id)]);
 return json({ok:true});}catch(e){return failure(e)}
}
