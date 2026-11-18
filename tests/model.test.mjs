import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {segments,phaseAt,search,nearest,challenge,signature} from '../web/model.mjs';
const data=JSON.parse(readFileSync(new URL('../web/data/lights.json',import.meta.url)));
const peggy=data.lights.find(r=>r.id==='atl-487');
test('official source examples preserve exact group order and intervals',()=>{
 assert.deepEqual(segments(peggy).bars,[1.5,3.5]);
 assert.deepEqual(segments(data.lights.find(r=>r.id==='pac-386')).bars,[.25,.75,.25,3.75]);
 assert.equal(phaseAt([1.5,3.5],1.6).on,false);
 assert.equal(phaseAt([1.5,3.5],5.2).on,true);
});
test('illustrations preserve period; unsupported sector and composite lights omit playback',()=>{
 const bars=segments({rhythm:'Fl(3)',colour:'W',period:12}).bars;
 assert.equal(bars.length,6);assert.equal(bars.reduce((a,b)=>a+b,0),12);
 assert.deepEqual(segments({rhythm:'Q(6) + LFl',colour:'W',period:15}).bars,[]);
 assert.deepEqual(segments({rhythm:'F',colour:'W R G'}).bars,[]);
});
test('search ignores curly apostrophes; nearest excludes selected and orders by distance',()=>{
 assert.deepEqual(search(data.lights,data.sections,'Peggy’s Point','Atlantic').map(r=>r.id),[peggy.id]);
 const near=nearest(data.lights,peggy,3);
 assert.ok(near.every((r,i)=>r.light.id!==peggy.id && (!i || r.km>=near[i-1].km)));
});
test('each question has three distinct signals and one valid answer',()=>{
 const q=challenge(data.lights);assert.equal(new Set(q.choices.map(signature)).size,3);
 assert.ok(q.choices.includes(q.target));assert.equal(challenge([peggy]),null);
});
