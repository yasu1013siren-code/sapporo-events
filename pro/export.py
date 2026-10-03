"""Read-only beta exporter; never runs collectors or publishes."""
import argparse, json, re, sqlite3, unicodedata
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from zoneinfo import ZoneInfo

def safe_url(value):
    try:
        p=urlsplit(value)
        if p.scheme not in ('http','https') or not p.hostname or p.username or p.password: return ''
        return urlunsplit((p.scheme,p.netloc,p.path,urlencode([(k,v) for k,v in parse_qsl(p.query) if not k.startswith('utm_')]),''))
    except ValueError: return ''

def dates(text):
    s=unicodedata.normalize('NFKC',text or '')
    found=[]
    # Explicit year required. Omitted range end inherits year/month, including Dec->Jan.
    pattern=r'(\d{4})\s*(?:年|[-/])\s*(\d{1,2})\s*(?:月|[-/])\s*(\d{1,2})\s*日?'
    for m in re.finditer(pattern,s):
        try: found.append(date(*map(int,m.groups())))
        except ValueError: return None,None
    if not found:return None,None
    tail=s[re.search(pattern,s).end():]
    short=re.match(r'\s*(?:\([^)]*\))?\s*[〜～~–－-]\s*(?:(\d{1,2})\s*(?:月|/)\s*)?(\d{1,2})\s*日?',tail)
    if len(found)==1 and short:
        month=int(short[1] or found[0].month); year=found[0].year+(month<found[0].month)
        try:found.append(date(year,month,int(short[2])))
        except ValueError:return None,None
    return min(found).isoformat(),max(found).isoformat()

def normalize(rows):
    result={}
    for row in rows:
        r=dict(row)
        # Explicit republication restriction observed during beta research.
        if 'サツイベ' in (r.get('source') or ''): continue
        url=safe_url(r.get('url',''))
        if not url:continue
        start,end=dates(r.get('date_text',''))
        # Source labels may be stale; never infer location from source alone.
        place=r.get('place') or ''; text=place+' '+(r.get('title') or '')
        wards=re.findall(r'(中央|北|東|西|南|白石|豊平|清田|厚別|手稲)区',place)
        area='すすきの' if re.search('すすきの|ススキノ|SUSUKINO',text,re.I) else ('中央区' if wards==['中央'] or (not wards and re.search('大通公園|狸小路|札幌駅前通地下歩行空間',place)) else '地区未確認/その他')
        kind='開店閉店' if re.search('開店|閉店|オープン|OPEN|閉業',text,re.I) else 'イベント'
        item={k:r.get(k) or '' for k in ('title','place','source','date_text','categories','last_seen','published_date')}
        item.update(url=url,start=start,end=end,area=area,kind=kind,date_status='年付き表記から解析・原文確認' if start else '日時不明・年省略/要確認',prediction=bool(re.search('予定|予測|見込み',r.get('date_text','')+' '+text)))
        key=(unicodedata.normalize('NFKC',item['title']).strip(),start,end,place)
        if key not in result or item['last_seen']>result[key]['last_seen']:result[key]=item
    return sorted(result.values(),key=lambda x:(x['start'] or '9999',x['title']))

def export(db,out):
    # mode=ro prevents accidentally creating an empty database on path errors.
    with sqlite3.connect(Path(db).resolve().as_uri()+'?mode=ro',uri=True) as conn:
        conn.row_factory=sqlite3.Row
        events=normalize(conn.execute('select * from events'))
    payload={'generated_at':datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),'events':events,'note':'last_seenは収集確認日。情報源自体の更新日時ではありません。取得成功は保証しません。'}
    dest=Path(out);dest.parent.mkdir(parents=True,exist_ok=True)
    temp=dest.with_suffix('.tmp');temp.write_text(json.dumps(payload,ensure_ascii=False),encoding='utf-8');temp.replace(dest)
    return len(events)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--db',default='data/events.db');p.add_argument('--out',default='data/pro-events.json');a=p.parse_args();print(f'{export(a.db,a.out)} records exported')
