export const colours = { W: 'White', R: 'Red', G: 'Green', Y: 'Yellow', Bu: 'Blue', Or: 'Orange', Am: 'Amber' };
const families = {Fl:'Flashing', LFl:'Long-flashing', F:'Fixed', Q:'Quick-flashing', VQ:'Very quick-flashing', Oc:'Occulting', Iso:'Isophase', Mo:'Morse', Al:'Alternating'};

export function family(code) {
  const base = Object.keys(families).find(k => code === k || code.startsWith(k+'('));
  return families[base] || 'Composite signal';
}

export function signature(light) {
  return [light.rhythm, light.colour, light.period ? light.period+'s' : ''].filter(Boolean).join(' ');
}

export function segments(light) {
  if (!colours[light.colour]) return {note:'The source lists multiple colours or sectors. See the official table for viewing directions.', bars:[]};
  if (light.rhythm === 'F') return {note:'Continuous light.', bars:[1], fixed:true};
  const period = light.period;
  if (!(period > 0)) return {note:'The source gives no single period for this entry.', bars:[]};
  if (light.durations) return {note:'Flash and eclipse durations from the source remarks.', bars:light.durations, exact:true};
  if (light.rhythm === 'Iso') return {note:'Equal light and dark intervals, as defined by isophase.', bars:[period/2,period/2], exact:true};
  if (light.rhythm === 'Oc') return {note:'Illustrated timing. The published period is exact; the eclipse width is approximate.',bars:[period*.75, period*.25]};
  if (/^(Fl|LFl|Q|VQ)(?:\((\d+)\))?$/.test(light.rhythm)) {
    const count = Number(light.rhythm.match(/\((\d+)\)/)?.[1] ?? 1);
    const unit = period/(2*count+2);
    const bars = Array.from({length:count*2},(_,i)=>i===count*2-1 ? period-(count*2-1)*unit : unit);
    return {note:'Illustrated timing. Flash count and period are published; individual durations are approximate.',bars};
  }
  return {note:'Read the full notation in the official table. This compound rhythm has no simple playback here.',bars:[]};
}

export function phaseAt(bars,elapsed) {
  const total = bars.reduce((a,b)=>a+b,0);
  if (!total) return {on:false,fraction:0};
  const time = (elapsed%total+total)%total;
  let boundary = 0;
  for (let i=0;i<bars.length;i++) {
    boundary += bars[i];
    if (time < boundary) return {on:i%2===0,fraction:time/total};
  }
  return {on:false,fraction:1};
}

export function distance(a,b) {
  const rad = Math.PI/180, dlat=(b.lat-a.lat)*rad, dlon=(b.lon-a.lon)*rad;
  const h=Math.sin(dlat/2)**2+Math.cos(a.lat*rad)*Math.cos(b.lat*rad)*Math.sin(dlon/2)**2;
  return 12742*Math.asin(Math.min(1,Math.sqrt(h)));
}

export function nearest(lights,light,limit=6) {
  return lights.filter(r=>r.id!==light.id).map(r=>({light:r,km:distance(light,r)})).sort((a,b)=>a.km-b.km).slice(0,limit);
}

export function search(lights, sections, query, coast) {
  const normalize=s=>s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f’']/g,'');
  const words = normalize(query.trim()).split(/\s+/).filter(Boolean);
  return lights.filter(r=>{
    const section=sections[r.section];
    if (coast && section.volume!==coast) return false;
    const hay=normalize([r.name,r.number,section.area,section.volume,signature(r),colours[r.colour]||''].join(' '));
    return words.every(w=>hay.includes(w));
  });
}

// Options differ by observable characteristic so each exercise has one answer.
export function challenge(records,random=Math.random) {
  const candidates=records.filter(r=>r.period && segments(r).bars.length && colours[r.colour]);
  const pool=candidates.slice();
  for (let i=pool.length-1;i>0;i--) {
    const j=Math.floor(random()*(i+1));
    [pool[i],pool[j]]=[pool[j],pool[i]];
  }
  const choices=[], signatures=new Set(), names=new Set();
  for(const r of pool){
    const key=signature(r);
    if (!signatures.has(key) && !names.has(r.name)) {
      choices.push(r); signatures.add(key); names.add(r.name);
    }
    if(choices.length===3) break;
  }
  return choices.length===3 ? {choices,target:choices[Math.floor(random()*choices.length)]} : null;
}
