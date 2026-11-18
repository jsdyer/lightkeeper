import {challenge,colours,family,nearest,phaseAt,search,segments,signature} from './model.mjs';
const $ = id => document.getElementById(id);
const make = (tag, value, className) => {
  const node=document.createElement(tag);
  if (value!=null) node.textContent=value;
  if(className) node.className=className;
  return node;
};
const swatches = {R:'#ff7d78',G:'#77dc97',Y:'#ffe26d',W:'#f8f7e9',Bu:'#78bbff',Or:'#ffb175',Am:'#ffc772'};
let data, selected, results=[], limit=35, map, layer, marker, guess;
const players = new Set();

function stopPlayback() { for(const stop of [...players]) stop(); }
document.addEventListener('visibilitychange',()=>{if(document.hidden) stopPlayback();});

function renderSignal(parent, light, interactive) {
  const pattern=segments(light);
  const box=make('div');
  const supported = pattern.bars.length>0;
  if(supported) {
    const track=make('div',null,'track');
    track.setAttribute('role','img');
    const notes=pattern.bars.map((seconds,i)=>(i%2?'dark ':'lit ')+Number(seconds.toFixed(3))+' s');
    track.setAttribute('aria-label',pattern.fixed ? 'Continuous light' : notes.join(', '));
    for (const [i,width] of pattern.bars.entries()) {
      const bar=make('span',null,'bar');
      bar.style.flexGrow=width;
      bar.style.background=i%2?'#1b3139':swatches[light.colour];track.append(bar);
    }
    box.append(track);
    if(interactive && !pattern.fixed) {
      const needle=make('i',null,'needle');needle.hidden=true;track.append(needle);
      const controls=make('div',null,'sig-controls');
      const button=make('button','Play signal','control');button.type='button';
      const bulb=make('span',null,'bulb');bulb.setAttribute('aria-hidden','true');
      // Slow movements use a small lamp. Higher rates use a steady lamp and a moving cursor.
      const starts=pattern.bars.map((_,i)=>i).filter(i=>i%2===0);
      const minInterval=Math.min(...starts.map(i=>pattern.bars[i]+(pattern.bars[i+1]||0)));
      const pulse=minInterval>=.5 && !matchMedia('(prefers-reduced-motion: reduce)').matches;
      const stop=()=>{
        cancelAnimationFrame(frame);frame=0;players.delete(stop);
        button.textContent='Play signal';button.setAttribute('aria-pressed','false');
        needle.hidden=true;bulb.style.background='transparent';
      };
      let frame=0;
      button.setAttribute('aria-pressed','false');
      button.onclick=()=>{
        if(frame){stop();return;}
        stopPlayback();players.add(stop);
        const start=performance.now();needle.hidden=false;
        button.textContent='Pause signal';button.setAttribute('aria-pressed','true');
        const tick=now=>{
          const phase=phaseAt(pattern.bars,(now-start)/1000);
          needle.style.left=phase.fraction*100+'%';
          bulb.style.background=(!pulse||phase.on)?swatches[light.colour]:'transparent';
          frame=requestAnimationFrame(tick);
        };frame=requestAnimationFrame(tick);
      };
      controls.append(button,bulb,make('small',pulse?'':'Timing cursor'));box.append(controls);
    }
  }
  box.append(make('p',pattern.note,'note'));
  if(light.durations) box.append(make('p',light.durations.map((s,i)=>(i%2?'Dark ':'Lit ')+s+' s').join(' · '),'note'));
  parent.append(box);
}

function detailCard(light) {
  const card=make('article');
  card.append(make('h3',light.name),make('p',signature(light)+' · '+(colours[light.colour]||light.colour)));
  renderSignal(card,light,false);
  return card;
}

function compare(){
  const other=data.lights.find(r=>r.id===$('near').value);
  if(other) $('comparison').replaceChildren(detailCard(selected),detailCard(other));
}

function records(){
  const list=$('rows');list.replaceChildren();
  for(const r of results.slice(0,limit)){
    const button=make('button',null,'row');button.type='button';button.setAttribute('aria-pressed',String(r.id===selected?.id));
    button.append(make('span',r.name),make('span',signature(r)));button.onclick=()=>select(r,true);list.append(button);
  }
  $('more').hidden=limit>=results.length;
  $('listcount').textContent=results.length?'Showing '+Math.min(limit,results.length)+' of '+results.length.toLocaleString()+' matching lights.':'No matches. Try a shorter name or another coast.';
}

function select(light,focusMap) {
  stopPlayback();selected=light;
  const section=data.sections[light.section];
  $('name').textContent=light.name;$('volume').textContent=section.volume+' · LL '+light.number;
  $('area').textContent=section.area;$('signal').textContent=signature(light);
  $('preview').replaceChildren();renderSignal($('preview'),light,true);
  const facts=[['Light character',family(light.rhythm)],['Colour',colours[light.colour]||light.colour],
    ['Focal height',light.height==null?'Unlisted':light.height+' m'],['Nominal range',light.range==null?'Unlisted':light.range+' NM'],
    ['Latitude',light.lat.toFixed(5)+'° N'],['Longitude',(-light.lon).toFixed(5)+'° W']];
  $('facts').replaceChildren(...facts.map(([k,v])=>{const d=make('div'); d.append(make('dt',k),make('dd',v));return d;}));
  $('source').href=section.url;$('sectiondate').textContent='Section correction '+section.correction+' · see LL '+light.number;
  const hash='#light='+encodeURIComponent(light.id);
  $('deep').href=hash;
  if(focusMap) history.replaceState(null,'',hash);
  if(map){
    if(marker)marker.remove();
    if(focusMap)map.setView([light.lat,light.lon],Math.max(map.getZoom(),11));
    marker=L.circleMarker([light.lat,light.lon],{radius:10,color:'#0c293a',fillColor:'#e8ad34',fillOpacity:.96,weight:3}).addTo(map);
    marker.bindTooltip(make('span',light.name)).openTooltip();
  }
  const neighbours=nearest(data.lights,light);
  $('near').replaceChildren(...neighbours.map(({light:r,km})=>new Option(r.name+' · '+km.toFixed(1)+' km',r.id)));
  compare();records();
}

function mapPoints(){
  if(!map)return;
  layer.clearLayers();
  const bounds=map.getBounds().pad(.05);
  const visible=results.filter(r=>bounds.contains([r.lat,r.lon]));
  // Sample when looking at an entire coast; individual stations expand as you zoom.
  const step=Math.max(1,Math.ceil(visible.length/650));
  for(let i=0;i<visible.length;i+=step){
    const r=visible[i];
    L.circleMarker([r.lat,r.lon],{radius:4,color:'#183b43',weight:1.5,fillColor:swatches[r.colour]||'#e4ba79',fillOpacity:.95})
      .bindTooltip(make('span',r.name)).on('click',()=>select(r,true)).addTo(layer);
  }
  if(marker)marker.bringToFront();
}
function filter(move){
  results=search(data.lights,data.sections,$('query').value,$('coast').value);limit=35;
  $('matches').textContent=results.length.toLocaleString()+' matches · zoom for detail';records();
  if(move && results.length){
    if(map) map.fitBounds(L.latLngBounds(results.map(r=>[r.lat,r.lon])),{maxZoom:11,padding:[15,15]});
    if(!results.includes(selected))select(results[0],false);
  }
  mapPoints();
}

function exercise(){
  stopPlayback();
  guess=challenge(data.lights.filter(r=>!$('coast').value || data.sections[r.section].volume===$('coast').value));
  $('clue').replaceChildren();$('options').replaceChildren();$('answer').textContent='';
  if(!guess)return;
  const r=guess.target;
  $('clue').append(make('p',(colours[r.colour]||r.colour)+' · '+family(r.rhythm)+' · one cycle every '+r.period+' s'));
  renderSignal($('clue'),r,true);
  for(const light of guess.choices){
    const option=make('button',light.name+' · '+signature(light));option.type='button';
    option.onclick=()=>{
      if(light.id!==r.id){option.disabled=true;$('answer').textContent='Try another light. Compare the colour, flash group and period.';return;}
      for(const b of $('options').children)b.disabled=true;
      $('answer').textContent='Correct. '+r.name+' shows '+signature(r)+'. ';
      const link=make('button','Open this record');link.onclick=()=>{select(r,true);$('name').scrollIntoView({block:'center'});};$('answer').append(link);
    };
    $('options').append(option);
  }
}

async function open(){
  const response=await fetch('./data/lights.json');
  if(!response.ok)throw Error('Unable to load index');
  data=await response.json();
  const initial=data.lights.find(r=>r.id===new URLSearchParams(location.hash.slice(1)).get('light'))
    ||data.lights.find(r=>r.id==='atl-487')||data.lights[0];
  if(window.L){
    map=L.map('map',{preferCanvas:true,scrollWheelZoom:false}).setView([initial.lat,initial.lon],11);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(map);
    layer=L.layerGroup().addTo(map);map.on('moveend',mapPoints);
  }
  $('coverage').textContent=data.lights.length.toLocaleString()+' lights · 3 Coast Guard volumes';
  $('dates').textContent=(data.retrieved ? 'Index retrieved '+data.retrieved : 'Retrieval date unrecorded')+'. Covers '+Object.keys(data.sections).length+' sections. '+data.omitted+' source rows lack a usable characteristic, position or identifier and are excluded.';
  $('query').oninput=()=>filter(true);$('coast').onchange=()=>{filter(true);exercise();};
  $('near').onchange=compare;$('more').onclick=()=>{limit+=35;records();};$('new').onclick=exercise;
  window.addEventListener('hashchange',()=>{const id=new URLSearchParams(location.hash.slice(1)).get('light');const r=data.lights.find(l=>l.id===id);if(r&&r!==selected)select(r,true);});
  filter(false);select(initial,false);exercise();
}
open().catch(()=>{$('coverage').textContent='The station index could not load. Reload or open the official Coast Guard volumes below.';});
