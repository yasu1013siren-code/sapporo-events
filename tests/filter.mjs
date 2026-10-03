import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';
const {selectEvents,tokyoDay}=await import('data:text/javascript;base64,'+Buffer.from(readFileSync('data/pro.js')).toString('base64'));
const e=(start,area='中央区',end=start)=>({start,end,area,kind:'イベント'});const s={area:'中央区',kind:'all',period:'future'};
assert.deepEqual(selectEvents([e('2026-10-09'),e('2026-10-10'),e('2026-11-02'),e('2026-11-03'),e(null)],s,'2026-10-03').map(x=>x.start),['2026-10-10','2026-11-02']);
assert.equal(selectEvents([e('2026-10-02'),e('2026-10-03'),e('2026-10-04'),e('2026-10-05'),e('2026-10-04','すすきの'),e('2026-10-03','地区未確認/その他')],{...s,period:'week'},'2026-10-03').length,3);
assert.equal(selectEvents([e('2026-12-25','中央区','2027-01-03')],{...s,period:'week'},'2026-12-31').length,1);
assert.equal(tokyoDay(new Date('2026-10-02T15:00:00Z')),'2026-10-03');assert.equal(selectEvents([] ,s).length,0);console.log('5 filter assertions passed');
