"""Build stable, offline light profiles and find exact nearest neighbours by published position."""
from bisect import bisect_left
from collections import defaultdict
from datetime import datetime
from html import escape
from math import asin, cos, radians, sin, sqrt
import re
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

BASE = 'https://coolcode.ca/lightkeeper/records/'
KEY = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
COLOURS = {'W':'white', 'R':'red', 'G':'green', 'Y':'yellow', 'Bu':'blue', 'Or':'orange', 'Am':'amber'}
GUIDE = 'https://www.canada.ca/en/canadian-coast-guard/corporate/publications/canadian-aids-navigation-system-2023.html'


def number(value):
    return f'{value:g}'


def key(light):
    value = light['id'].replace('.', '-d-')
    if not KEY.fullmatch(value):
        raise ValueError('Unexpected light identifier')
    return value


def signature(light):
    return ' '.join([light['rhythm'], light['colour']] + ([number(light['period'])+'s'] if light['period'] else []))


def interpretation(light):
    rhythm = light['rhythm']
    colours = ', '.join(COLOURS.get(k,k) for k in light['colour'].split())
    period = light['period']
    if ' ' in light['colour']:
        return f'The entry lists several colour indications ({colours}). Read the official section for how the indications apply at this position.'
    forms = {'F':f'A steady {colours} light.', 'Fl':f'A single {colours} flash.', 'LFl':f'A single long {colours} flash.',
             'Q':f'A quick-flashing {colours} light.', 'VQ':f'A very quick-flashing {colours} light.',
             'Oc':f'A {colours} light interrupted by an eclipse. The light lasts longer than the darkness.',
             'Iso':f'A {colours} light with equal light and dark intervals.',
             'Mo(A)':f'The {colours} light spells Morse A with a short flash followed by a long flash.',
             'Mo(D)':f'The {colours} light spells Morse D with a long flash and two short flashes.',
             'Fl(2+1)':f'Two {colours} flashes followed by one separate flash.',
             'Q(6) + LFl':f'Six quick {colours} flashes followed by a long flash.',
             'VQ(6) + LFl':f'Six very quick {colours} flashes followed by a long flash.'}
    phrase = forms.get(rhythm)
    group = re.fullmatch(r'(Fl|Q|VQ|Oc)\((\d+)\)', rhythm)
    if group:
        modifier = {'Fl':'', 'Q':' quick', 'VQ':' very quick', 'Oc':''}[group[1]]
        phrase = (f'A {colours} light with {group[2]} eclipses in each group.' if group[1]=='Oc'
                  else f'A group of {group[2]}{modifier} {colours} flashes.')
    if not phrase:
        phrase = f'The Coast Guard lists the {colours} signal as {rhythm}. See the original table for its full pattern.'
    if period and rhythm != 'F':
        return phrase + f' The complete cycle repeats every {number(period)} seconds.'
    return phrase


def distance(a,b):
    rad = radians(1)
    h = sin((a['lat']-b['lat'])*rad/2)**2 + cos(a['lat']*rad)*cos(b['lat']*rad)*sin((a['lon']-b['lon'])*rad/2)**2
    return 12742 * asin(sqrt(min(1,h)))


class Neighbours:
    def __init__(self, records):
        self.rows = sorted(records, key=lambda r:r['lat'])
        self.latitudes = [r['lat'] for r in self.rows]

    def closest(self, light, count):
        # Absolute latitude separation is a lower bound on great-circle distance.
        # Visit candidates in ascending lower-bound order and stop once no closer
        # result is possible. The secondary ID ordering breaks co-located ties.
        right = bisect_left(self.latitudes,light['lat'])
        left = right-1
        best = []
        while left >= 0 or right < len(self.rows):
            below = light['lat']-self.latitudes[left] if left>=0 else float('inf')
            above = self.latitudes[right]-light['lat'] if right<len(self.rows) else float('inf')
            if len(best)==count and 6371*radians(min(above,below)) > best[-1][0]:
                break
            if below <= above:
                other=self.rows[left]
                left-=1
            else:
                other=self.rows[right]
                right+=1
            if other['id'] != light['id']:
                best.append((distance(light,other),other['id'],other))
                best.sort(key=lambda item:(item[0],item[1]))
                del best[count:]
        return [(d,r) for d,_,r in best]


def htmlpage(route,title,summary,body):
    root = '../../' if route else '../'
    canonical = BASE + route
    return f'''<!doctype html>
<html lang="en-CA"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{escape(title)} · Lightkeeper</title><meta name="description" content="{escape(summary,quote=True)}"><link rel="canonical" href="{canonical}"><link rel="stylesheet" href="{root}style.css"><script defer src="/assets/tool-metrics.js" referrerpolicy="no-referrer"></script></head>
<body class="records-page" data-tool="lightkeeper"><header><nav aria-label="Site"><a href="{root}">Lightkeeper</a><a href="{root}records/">Light directory</a></nav></header><main>{body}</main><footer><p><a href="https://coolcode.ca/">CoolCode.ca</a> · <a href="{root}#sources">Sources</a></p><details class="credits"><summary>Coast Guard attribution</summary><p>Contains information published by the Canadian Coast Guard and Department of Fisheries and Oceans licensed under the <a href="https://www.canada.ca/en/canadian-coast-guard/corporate/publications/open-information-licence.html">Canadian Coast Guard Open Information Licence</a>. This Information is available in its original format for free download on the <a href="https://www.canada.ca/en/canadian-coast-guard.html">Canadian Coast Guard website</a> and the <a href="https://notmar.gc.ca/">Monthly Edition of the Notices to Mariners (NOTMAR) website</a>.</p></details></footer></body></html>'''


def section_key(code):
    if not KEY.fullmatch(code):
        raise ValueError('Unexpected section identifier')
    return 'section-'+code


def official_date(section):
    try:
        return datetime.strptime(section['correction'],'%m/%Y').strftime('%B %Y')
    except ValueError:
        return section['correction'] or 'unrecorded'


def permalink(light,view,other=None):
    params={'light':light['id'], 'view':view}
    if other:
        params['compare']=other['id']
    return '../../#'+escape(urlencode(params),quote=True)


def profile(light,section,retrieved,near,matching):
    name=escape(light['name'])
    num=escape(light['number'])
    chars=escape(signature(light))
    area=escape(section['area'])
    volume=escape(section['volume'])
    title=f"{light['name']} · {section['volume']} LL {light['number']} signal"
    summary=f"{light['name']} in {section['area']} shows {signature(light)}. {interpretation(light)}"
    rows=[('List number',f'{volume} LL {num}'),('Published position', f"{abs(light['lat']):.5f}° {'N' if light['lat']>=0 else 'S'}, {abs(light['lon']):.5f}° {'E' if light['lon']>=0 else 'W'}")]
    if light.get('height') is not None: rows.append(('Focal height',number(light['height'])+' m'))
    if light.get('range') is not None: rows.append(('Nominal range',number(light['range'])+' nautical miles'))
    facts=''.join(f'<div><dt>{label}</dt><dd>{value}</dd></div>' for label,value in rows)
    timing=''
    if light.get('durations'):
        phases=' · '.join(f'{"Lit" if i%2==0 else "Dark"} {number(t)} s' for i,t in enumerate(light['durations']))
        timing=f'<p><strong>Timing in the source remarks</strong><br>{phases}.</p>'
    elif light['rhythm']=='Iso' and light['period'] and ' ' not in light['colour']:
        timing=f'<p>Each half of the cycle lasts {number(light["period"]/2)} seconds.</p>'
    if light['rhythm']=='F' and ' ' not in light['colour']:
        action='View the steady signal'
    elif ' ' not in light['colour'] and light['period'] and (light.get('durations') or re.fullmatch(r'(Fl|LFl|Q|VQ)(\(\d+\))?|Iso|Oc',light['rhythm'])):
        action='Open signal player'
    else:
        action='Open signal details'
    def neighbour(item):
        km,other=item
        label=(f'{km:.1f} km' if km>=.1 else ('same published position' if km==0 else 'under 0.1 km'))
        where=escape(signature(other))
        display=escape(other['name'])
        number_text=escape(other['number'])
        return f'<li><a href="../{key(other)}/">{display} · LL {number_text}</a><span>{label} · {where}</span><a class="pair" href="{permalink(light,"compare",other)}">Compare both signals</a></li>'
    related='<h2>Nearest published positions</h2><p>Approximate straight-line distances from this light.</p><ul class="record-list">'+''.join(map(neighbour,near))+'</ul>' if near else ''
    same=''
    if matching:
        reason = ('Matches the rhythm, colour and listed period.' if light['period'] else
                  'Matches the published rhythm and colour. The source lists no cycle period for these entries.')
        same=f'<h2>Closest light with the same listed signal</h2><p>{reason}</p><ul class="record-list">'+neighbour(matching[0])+'</ul>'
    section_url=escape(section['url'],quote=True)
    check=f' Snapshot retrieved <time datetime="{retrieved}">{retrieved}</time>.' if retrieved else ' The snapshot has no recorded retrieval date.'
    context = ''
    if light['id']=='pac-387.2' and light['name']=='English Bay Anchorage East':
        context = ('<h2>Another record from English Bay</h2><p>The Ship Fund lists the container ship '
                   '<em>Europe</em> in English Bay on 21 January 2023. '
                   '<a href="https://coolcode.ca/spillledger/records/incidents/europe-2023-01-21-english-bay-vancouver-british-columbia/">'
                   'Read the English Bay incident record in Spill Ledger</a>.</p>')
    body=f'''<p class="record-kicker">{volume} · LL {num}</p><h1>{name}</h1><p><a href="../{section_key(light['section'])}/">{area}</a></p>
<section class="record-signal"><h2>{chars}</h2><p>{escape(interpretation(light))}</p>{timing}<div class="record-actions"><a href="{permalink(light,'signal')}">{action}</a><a href="{permalink(light,'map')}">Locate on the map</a></div></section>
<dl class="record-facts">{facts}</dl>{related}{same}{context}<h2>Coast Guard record</h2><p>Look for LL {num} in the <a href="{section_url}">{area} table</a>. Section correction edition {escape(official_date(section))}.{check}</p><p>Read the <a href="{GUIDE}">Coast Guard’s signal guide</a> for the notation. For navigation, use current official charts and notices.</p>'''
    return htmlpage(key(light)+'/', title, summary, body)


def generate(stage,snapshot):
    records=snapshot['lights']
    sections=snapshot['sections']
    output=stage/'records'
    output.mkdir()
    paths=[]
    def write(route,page):
        folder=output/route
        folder.mkdir(exist_ok=True)
        (folder/'index.html').write_text(page,encoding='utf-8')
        paths.append(BASE+route)
    ids={key(r) for r in records}
    if len(ids)!=len(records): raise ValueError('Light profile slug collision')
    geography=Neighbours(records)
    signatures=defaultdict(list)
    by_section=defaultdict(list)
    for r in records:
        signatures[signature(r)].append(r)
        by_section[r['section']].append(r)
    groups={chars:Neighbours(group) for chars,group in signatures.items()}
    for r in records:
        write(key(r)+'/',profile(r,sections[r['section']],snapshot.get('retrieved'),geography.closest(r,2),groups[signature(r)].closest(r,1)))
    volumes=defaultdict(list)
    for code,group in sorted(by_section.items(),key=lambda x:sections[x[0]]['area']):
        section=sections[code]
        area=section['area']
        volume=section['volume']
        count=len(group)
        route=section_key(code)+'/'
        volumes[volume].append(f'<li><a href="{route}">{escape(area)}</a> · {count:,} lights</li>')
        links=''.join(f'<li><a href="../{key(r)}/">{escape(r["name"])} · LL {escape(r["number"])}</a><span>{escape(signature(r))}</span></li>' for r in sorted(group,key=lambda r:(r['name'].casefold(),r['id'])))
        desc=f'{count:,} positioned lights in the {volume} volume for {area}. Open a list number to read its signal and compare nearby lights.'
        write(route,htmlpage(route,area+' · '+volume+' light directory',desc,f'<p class="record-kicker">{escape(volume)} volume</p><h1>{escape(area)}</h1><p>{escape(desc)}</p><p>Section correction edition {escape(official_date(section))}. <a href="{escape(section["url"],quote=True)}">Official Coast Guard table</a></p><ul class="record-list directory-list">{links}</ul>'))
    lights={r['id']:r for r in records}
    examples=[lights[i] for i in ('atl-487','pac-386','nl-1') if i in lights]
    sample=''.join(f'<li><a href="{key(r)}/">{escape(r["name"])}</a><span>{escape(signature(r))} · LL {escape(r["number"])}</span></li>' for r in examples)
    contents=''.join('<h2>'+escape(vol)+'</h2><ul class="section-list">'+''.join(volumes[vol])+'</ul>' for vol in sorted(volumes))
    desc=f'Browse {len(records):,} Canadian lights in {len(by_section)} Coast Guard sections. Read a light’s signal and compare nearby lights.'
    write('',htmlpage('', 'Canadian light profiles by Coast Guard section', desc, f'<h1>Canadian light directory</h1><p>{desc}</p><ul class="record-list samples">{sample}</ul>{contents}'))
    urls=ET.Element('urlset',xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for url in sorted(paths): ET.SubElement(ET.SubElement(urls,'url'),'loc').text=url
    ET.ElementTree(urls).write(stage/'sitemap.xml',encoding='utf-8',xml_declaration=True)
    return examples[0] if examples else (records[0] if records else None)
