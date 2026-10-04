"""Read-only restaurant PRO beta export. Standard library only; no network calls."""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import json
import re
import sqlite3
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

JST = timezone(timedelta(hours=9))
DATE_TOKEN = re.compile(r'(?:(\d{4})\s*[年/.-]\s*)?(\d{1,2})\s*[月/.-]\s*(\d{1,2})(?:\s*日)?')
DAY_END = re.compile(r'[〜～~]\s*(\d{1,2})\s*日')

def normalize(value):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', value or '')).casefold()

def safe_url(value):
    try:
        p = urlsplit(value or '')
        return value if p.scheme in ('https', 'http') and p.netloc and not p.username and not p.password else ''
    except ValueError:
        return ''

def canonical_url(value):
    p = urlsplit(safe_url(value))
    # Query strings are retained: they may identify distinct events.
    return urlunsplit((p.scheme, p.netloc.lower(), p.path.rstrip('/'), p.query, ''))

def parse_dates(text, anchor):
    """Use explicit year or source's last-seen year; never promote past dates to next year.
    Unsupported/invalid/indefinite dates are excluded instead of guessing an end date.
    """
    text = unicodedata.normalize('NFKC', text or '')
    tokens = list(DATE_TOKEN.finditer(text))
    if not tokens:
        return None
    result = []
    year, previous_month = anchor.year, None
    try:
        for token in tokens:
            y, month, day = token.groups()
            month = int(month)
            if y:
                year = int(y)
            elif previous_month == 12 and month == 1:
                year += 1
            result.append(date(year, month, int(day)))
            previous_month = month
        end_day = DAY_END.search(text[tokens[-1].end():])
        if end_day:
            last = result[-1]
            result.append(date(last.year, last.month, int(end_day[1])))
    except ValueError:
        return None
    # A trailing range marker without an endpoint is not a confirmed duration.
    tail = text[tokens[-1].end():]
    if re.search(r'[〜～~]\s*$', tail):
        return None
    return min(result), max(result)

def kind_for(row):
    text = (row['categories'] or '') + ' ' + (row['title'] or '')
    if any(w in text for w in ('閉店', 'オープン', '開店', '開閉店')):
        return '開店・閉店'
    if any(w in text.upper() for w in ('POPUP', 'POP UP', 'ポップアップ', '期間限定ショップ')):
        return 'POPUP'
    if any(w in text for w in ('催事', '物産展', 'フェア')):
        return '催事'
    if any(w in text for w in ('ライブ', 'コンサート', '音楽')):
        return 'ライブ'
    return 'イベント'

def region_for(place):
    text = normalize(place)
    if any(w in text for w in ('すすきの', 'susukino', 'zeppsapporo', '豊水')):
        return 'すすきの周辺'
    if any(w in text for w in ('大通', '丸井今井', '三越', '狸小路', 'parco', 'パルコ', '創成川', 'テレビ塔', 'hitaru')):
        return '大通周辺'
    if any(w in text for w in ('札幌駅', 'チカホ', '地下歩行', '大丸', 'ステラプレイス')):
        return '札幌駅周辺'
    if 'サッポロファクトリー' in text or '札幌市教育文化会館' in text:
        return '中央区'
    if any(w in text for w in ('北海きたえーる', '札幌ドーム', 'プレミストドーム')):
        return '豊平区'
    for city in ('千歳', '北広島', '苫小牧', '恵庭'):
        if city in text:
            return city
    for ward in ('中央区', '北区', '東区', '白石区', '豊平区', '南区', '西区', '厚別区', '手稲区', '清田区'):
        if ward in text:
            return ward
    return '所在地確認待ち'

def guidance(kind):
    return {
        'ライブ': '会場周辺の来店動向を確認。開演・終演時刻はリンク先で確認してください。',
        '催事': '買い物客の動きを確認し、ランチ・休憩需要の参考に。',
        'POPUP': '期間限定店の周辺動向を確認。近隣店舗との組み合わせを検討。',
        '開店・閉店': '近隣店の変化を確認し、自店のメニューや告知の参考に。',
        'イベント': '会場との位置関係を確認し、仕込み・配置・告知を検討。',
    }[kind]

def make_payload(db, today=None):
    today = today or datetime.now(JST).date()
    cutoff = today + timedelta(days=29)
    stats = dict(total=0, undated=0, outside_window=0, movies=0, cancelled=0, uncategorized=0, duplicates=0, unsafe_url=0)
    events, groups = [], {}
    with closing(sqlite3.connect(f'{Path(db).resolve().as_uri()}?mode=ro', uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute('SELECT source,title,date_text,place,categories,url,first_seen,last_seen,links FROM events ORDER BY last_seen DESC, url').fetchall()
    latest = max((r['last_seen'] or '' for r in rows), default='')
    for r in rows:
        stats['total'] += 1
        if not r['categories']:
            stats['uncategorized'] += 1
            continue
        if '映画' in r['categories']:
            stats['movies'] += 1
            continue
        if any(w in (r['title'] or '') for w in ('中止', '開催延期')):
            stats['cancelled'] += 1
            continue
        try:
            anchor = date.fromisoformat(r['last_seen'] or '')
        except ValueError:
            anchor = today
        dates = parse_dates(r['date_text'], anchor)
        if dates is None:
            stats['undated'] += 1
            continue
        start, end = dates
        if end < today or start > cutoff:
            stats['outside_window'] += 1
            continue
        if not safe_url(r['url']):
            stats['unsafe_url'] += 1
            continue
        # Never merge separate performances by title alone; dates and venue must match.
        key = (normalize(r['title']), start.isoformat(), end.isoformat(), normalize(r['place']))
        links = [{'label': r['source'] or '情報元', 'url': r['url']}]
        try:
            links += json.loads(r['links'] or '[]') if isinstance(json.loads(r['links'] or '[]'), list) else []
        except (ValueError, TypeError):
            pass
        safe_links = []
        seen_links = set()
        for link in links:
            if not isinstance(link, dict) or not safe_url(link.get('url')):
                continue
            u = canonical_url(link['url'])
            if u not in seen_links:
                safe_links.append({'label': str(link.get('label') or '情報元'), 'url': link['url']})
                seen_links.add(u)
        if key in groups:
            stats['duplicates'] += 1
            old = groups[key]
            known = {canonical_url(l['url']) for l in old['links']}
            old['links'] += [l for l in safe_links if canonical_url(l['url']) not in known]
            continue
        kind = kind_for(r)
        event = dict(id=hashlib.sha256('|'.join(key).encode()).hexdigest()[:16], title=r['title'], start=start.isoformat(), end=end.isoformat(), date_text=r['date_text'], place=r['place'] or '会場確認待ち', region=region_for(r['place']), kind=kind, guidance=guidance(kind), links=safe_links, first_seen=r['first_seen'] or '', last_seen=r['last_seen'] or '')
        groups[key] = event
        events.append(event)
    events.sort(key=lambda e: (e['start'], normalize(e['title']), e['id']))
    return dict(generated_date=today.isoformat(), latest_seen=latest, window_days=30, stats=stats, events=events)

def generate_pro(db, output, today=None):
    payload = make_payload(db, today)
    template = (Path(__file__).parent / 'pro' / 'template.html').read_text(encoding='utf-8')
    # Prevent embedded JSON from closing its script element.
    embedded = json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template.replace('__PRO_DATA__', embedded), encoding='utf-8')
    return payload

if __name__ == '__main__':
    cli = argparse.ArgumentParser()
    cli.add_argument('--db', default='data/events.db')
    cli.add_argument('--output', default='data/pro.html')
    cli.add_argument('--today', type=date.fromisoformat)
    args = cli.parse_args()
    payload = generate_pro(args.db, args.output, args.today)
    print(json.dumps({'events': len(payload['events']), 'stats': payload['stats']}, ensure_ascii=False))
