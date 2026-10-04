// Run after: python3 pro_beta.py --today 2026-10-04
// Requires Playwright and its Chromium (or PRO_CHROMIUM_PATH).
const assert=require('node:assert/strict'), fs=require('node:fs'), path=require('node:path');
const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.PRO_CHROMIUM_PATH?{executablePath:process.env.PRO_CHROMIUM_PATH,args:['--no-sandbox','--disable-dev-shm-usage','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']}: {})});
 const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});
 const page=await context.newPage(), errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.clock.install({time:new Date('2026-10-04T08:00:00Z')});
 await page.goto('file://'+path.resolve('data/pro.html'));
 const initial=await page.locator('.card').count();assert(initial>0);
 await page.getByLabel('タイトル・会場を検索').fill('zzzz-no-such-event');assert.equal(await page.locator('.card').count(),0);
 await page.getByRole('button',{name:'条件をリセット'}).click();assert.equal(await page.locator('.card').count(),initial);
 await page.locator('#region').selectOption('大通周辺');assert(await page.locator('.card').count()<initial);
 await page.getByRole('button',{name:'条件をリセット'}).click();
 const first=page.locator('.card').first();
 await first.locator('.star').click();await first.getByLabel('営業メモ').fill('=SUM(1,1)');
 await page.getByLabel('保存した予定だけ表示').check();assert.equal(await page.locator('.card').count(),1);
 await page.reload();assert.equal(await page.locator('.card').count(),1);assert.equal(await page.locator('.card textarea').inputValue(),'=SUM(1,1)');
 const downloadPromise=page.waitForEvent('download');await page.getByRole('button',{name:'CSVを保存',exact:true}).click();const download=await downloadPromise;
 const csv=fs.readFileSync(await download.path(),'utf8');assert(csv.includes("'=SUM(1,1)"));
 await page.getByRole('button',{name:'スタッフ共有用まとめ'}).click();assert(await page.locator('#digest-dialog').isVisible());assert((await page.locator('#digest-text').inputValue()).includes('営業メモ：=SUM(1,1)'));
 await page.getByRole('button',{name:'閉じる',exact:true}).click();
 await page.locator('[name=business]').selectOption('居酒屋・バー');await page.locator('[name=uses_per_week]').fill('4');await page.locator('[name=minutes_saved]').fill('20');await page.locator('[name=useful_feature]').selectOption('地域・期間の絞り込み');await page.locator('[name=willingness]').selectOption('継続したい');
 const surveyPromise=page.waitForEvent('download');await page.getByRole('button',{name:'回答ファイルを保存'}).click();const survey=await surveyPromise;
 const answer=JSON.parse(fs.readFileSync(await survey.path(),'utf8'));assert.equal(answer.price_yen,500);assert.equal(answer.willingness,'継続したい');
 await page.getByRole('button',{name:'条件をリセット'}).click();
 await page.locator('.card textarea').first().fill('');await page.locator('.card .star').first().click();
 await page.evaluate(()=>window.scrollTo(0,0));
 fs.mkdirSync('docs/screenshots',{recursive:true});
 await page.screenshot({path:'docs/screenshots/pro-desktop.png'});
 for(const width of [320,375,390,768]){
  await page.setViewportSize({width,height:900});await page.evaluate(()=>window.scrollTo(0,0));
  const bounds=await page.evaluate(()=>({viewport:innerWidth,doc:document.documentElement.scrollWidth,cards:getComputedStyle(document.getElementById('cards')).gridTemplateColumns}));
  assert(bounds.doc<=bounds.viewport,`horizontal overflow at ${width}: ${JSON.stringify(bounds)}`);
  if(width===390)await page.screenshot({path:'docs/screenshots/pro-mobile.png'});
 }
 // Snapshot stays open across a day change: expired entries disappear without regeneration.
 await page.clock.setFixedTime(new Date('2026-11-05T08:00:00Z'));await page.reload();const payload=JSON.parse(fs.readFileSync('data/pro.html','utf8').split('<script id="pro-data" type="application/json">')[1].split('</script>')[0]);const remaining=payload.events.filter(e=>e.end>='2026-11-05'&&e.start<='2026-12-04');assert.equal(await page.locator('.card').count(),remaining.length);assert(remaining.length<initial);assert(await page.locator('#freshness').isVisible());
 assert.deepEqual(errors,[]);
 console.log(JSON.stringify({initial_cards:initial,viewports:[320,375,390,768,1440],checks:['search','region','favorites','notes-reload','csv-formula-escape','digest','survey-download','expired-on-view','no-console-errors']}));
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
