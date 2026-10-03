import unittest, tempfile, sqlite3
from pathlib import Path
from pro.export import dates,normalize,safe_url,export
class Beta(unittest.TestCase):
 def test_dates(self):
  self.assertEqual(dates('2026年12月30日〜1月3日'),('2026-12-30','2027-01-03'))
  self.assertEqual(dates('2026年10月3日〜4日'),('2026-10-03','2026-10-04'))
  self.assertEqual(dates('10月3日'),(None,None))
  self.assertEqual(dates('2026年2月30日'),(None,None))
 def test_duplicates_area_and_safety(self):
  row=dict(title='<img onerror=alert(1)>',url='https://example.org/a?utm_source=x',place='札幌市北区',source='中央区収集',date_text='2026年10月3日',last_seen='2026-10-02')
  got=normalize([row,{**row,'url':'https://example.org/b','last_seen':'2026-10-03'}]);self.assertEqual(len(got),1);self.assertEqual(got[0]['last_seen'],'2026-10-03');self.assertEqual(got[0]['area'],'地区未確認/その他')
  self.assertEqual(normalize([{**row,'url':'javascript:alert(1)'}]),[])
  self.assertEqual(normalize([{**row,'source':'サツイベ(中央区)'}]),[])
  self.assertEqual(safe_url('https://user:password@example.org'), '')
 def test_empty_and_failure_preserves_output(self):
  with tempfile.TemporaryDirectory() as td:
   db=Path(td)/'db';out=Path(td)/'out.json';c=sqlite3.connect(db);c.execute('create table events(url text)');c.close()
   self.assertEqual(export(db,out),0);before=out.read_bytes()
   with self.assertRaises(sqlite3.OperationalError):export(Path(td)/'missing',out)
   self.assertEqual(out.read_bytes(),before)
if __name__=='__main__':unittest.main()
