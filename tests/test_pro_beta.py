import ast
import json
import re
import unicodedata
import sqlite3
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
import pro_beta as pro

TODAY = date(2026, 10, 4)

class Dates(unittest.TestCase):
    def test_explicit_and_abbreviated_ranges(self):
        for text, expected in [('2026年9月30日〜10月6日', (date(2026,9,30),date(2026,10,6))), ('10月4日〜6日', (TODAY,date(2026,10,6))), ('2026/12/30〜1/2', (date(2026,12,30),date(2027,1,2))), ('2026-10-04 (日)', (TODAY,TODAY))]:
            self.assertEqual(pro.parse_dates(text, TODAY), expected)
    def test_past_dates_never_roll_forward(self):
        self.assertEqual(pro.parse_dates('1月1日', TODAY), (date(2026,1,1),date(2026,1,1)))
    def test_invalid_unknown_and_open_end(self):
        for text in ('未定', '2026年2月30日', '10月4日〜'):
            self.assertIsNone(pro.parse_dates(text, TODAY))

class Export(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name)/'events.db'
        with sqlite3.connect(self.db) as c:
            c.execute('CREATE TABLE events(source,title,date_text,place,categories,url,first_seen,last_seen,links)')
    def tearDown(self):
        self.tmp.cleanup()
    def insert(self,title='Test',dt='2026年10月5日',place='大通公園',url='https://example.com/1',cat='イベント',links='[]'):
        with sqlite3.connect(self.db) as c:
            c.execute('INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?)', ('公式',title,dt,place,cat,url,'2026-10-04','2026-10-04',links))
    def test_past_today_future_window_and_movies(self):
        for title,dt in [('past','2026年10月3日'),('today','2026年10月4日'),('future','2026年11月2日'),('later','2026年11月3日'),('unknown','未定')]:
            self.insert(title=title,dt=dt,url='https://example.com/'+title)
        self.insert(title='movie',cat='🍿 公開予定映画')
        self.insert(title='cancelled 中止')
        p=pro.make_payload(self.db,TODAY)
        self.assertEqual([e['title'] for e in p['events']],['today','future'])
        self.assertEqual(p['stats']['movies'],1)
    def test_duplicates_merge_links_without_merging_different_days_or_venues(self):
        self.insert(title='Ａ Ｂ',url='https://a.example/1')
        self.insert(title='A B',url='https://b.example/2')
        self.insert(title='A B',dt='2026年10月6日',url='https://c.example/3')
        self.insert(title='A B',place='Zepp Sapporo',url='https://d.example/4')
        p=pro.make_payload(self.db,TODAY)
        self.assertEqual(len(p['events']),3)
        self.assertEqual(p['stats']['duplicates'],1)
        self.assertEqual(len(next(e for e in p['events'] if e['place']=='大通公園' and e['start']=='2026-10-05')['links']),2)
    def test_read_only_and_safe_embedded_json(self):
        self.insert(title='</script><img src=x onerror=alert(1)>',links='[{"url":"javascript:alert(1)"}]')
        before=self.db.read_bytes()
        output=Path(self.tmp.name)/'pro.html'
        p=pro.generate_pro(self.db,output,TODAY)
        self.assertEqual(before,self.db.read_bytes())
        self.assertNotIn('</script><img',output.read_text())
        self.assertEqual(len(p['events'][0]['links']),1)
        embedded=output.read_text().split('<script id="pro-data" type="application/json">')[1].split('</script>')[0]
        self.assertEqual(json.loads(embedded),p)
    def test_reject_unsafe_primary_url(self):
        self.insert(url='javascript:alert(1)')
        self.assertEqual(pro.make_payload(self.db,TODAY)['events'],[])
    def test_stable_id_for_saved_notes(self):
        self.insert()
        first=pro.make_payload(self.db,TODAY)['events'][0]['id']
        self.assertEqual(first,pro.make_payload(self.db,TODAY+timedelta(days=1))['events'][0]['id'])

class FreeSiteMovieRegression(unittest.TestCase):
    def test_existing_db_movies_removed_from_future_page(self):
        tree=ast.parse(Path('sapporo_chuo_collector.py').read_text())
        names={'parse_date_range','is_future_movie_row','filter_within_month','split_started_and_upcoming','build_html','_dedupe_display_rows','normalize','enforce_category_rules','sort_key_for_display','escape_html'}
        nodes=[n for n in tree.body if (isinstance(n,ast.FunctionDef) and n.name in names) or (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in {'_FULL_DATE_RE','_SHORT_DATE_RE','_SHORT_SLASH_DATE_RE'} for t in n.targets))]
        ns=dict(re=re,date=date,datetime=datetime,timedelta=timedelta,json=json,unicodedata=unicodedata,CATEGORY_ORDER=['🍿 公開予定映画','🎬 映画'],NON_EVENT_CATEGORY='news',DEPARTMENT_CATEGORY='department')
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'collector','exec'),ns)
        def row(dt,cat='🍿 公開予定映画'):return ('s','t',dt,'','','',cat,'u','','','')
        rows=[row('2026年9月25日公開'),row('2026年10月4日公開'),row('2026年10月5日公開'),row('未定')]
        filtered=ns['filter_within_month'](rows,TODAY)
        self.assertEqual(filtered,[rows[2]])
        self.assertEqual(ns['split_started_and_upcoming'](rows,TODAY),([],[rows[2]]))
        self.assertTrue(ns['is_future_movie_row'](row('上映中','🎬 映画'),TODAY))
        # Full HTML path uses a date object even though build_html receives ISO text.
        html=ns['build_html'](rows,'2026-10-04',0,page_kind='upcoming')
        self.assertNotIn('2026年9月25日公開',html)
        self.assertNotIn('2026年10月4日公開',html)
        self.assertIn('2026年10月5日公開',html)
        distinct=[('s','同じ公演','2026年10月5日','','Zepp Sapporo','','🎵 音楽ライブ','u1','','',''),('s','同じ公演','2026年10月6日','','Zepp Sapporo','','🎵 音楽ライブ','u2','','','')]
        self.assertEqual(len(ns['_dedupe_display_rows'](distinct)),2)

if __name__ == '__main__':unittest.main()
