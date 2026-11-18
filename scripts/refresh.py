"""Build a read-only light-characteristic index from Canadian Coast Guard tables."""
import argparse
from collections import Counter
from hashlib import sha256
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from lxml import html

INDEX = 'https://notmar.gc.ca/list-lights'
ROOT = Path(__file__).resolve().parents[1]
VOLUMES = {'pac': 'Pacific', 'atl': 'Atlantic', 'nl': 'Newfoundland and Labrador'}
SECTION = re.compile(r'/publications/list-lights/(?:atl/atl|pac/pac|newfoundland/nl)\d+-en\.php$')
DMS = re.compile(r'(?<![\d.])(\d{1,3})\s+(\d{1,2})\s+(\d{1,2}(?:\.\d+)?)(?![\d.])')


def fetch(url):
    request = Request(url, headers={'User-Agent': 'CoolCode Lightkeeper educational index (coolcode.ca/lightkeeper/)'})
    with urlopen(request, timeout=45) as reply:
        return reply.read()


def text(cell):
    return ' '.join(' '.join(cell.itertext()).split())


def number(value):
    return float(value) if re.fullmatch(r'\d+(?:\.\d+)?', value) else None


def sections(data):
    result = {}
    for row in html.fromstring(data, parser=html.HTMLParser(encoding='utf-8')).xpath('//tr[td]'):
        cells = row.xpath('./td')
        links = [p for p in row.xpath('.//a/@href') if SECTION.fullmatch(p)]
        if not links:
            continue
        path = links[0]
        code = path.split('/')[-1].split('-')[0]
        volume = re.match(r'[a-z]+', code)[0]
        result[code] = {'area': text(cells[1]), 'volume': VOLUMES[volume],
                        'correction': text(cells[2]), 'url': urljoin(INDEX, path)}
    if len(result) < 55 or {s['volume'] for s in result.values()} != set(VOLUMES.values()):
        raise ValueError('Unexpected NOTMAR catalogue format or missing volume')
    return result


def coordinate(group, limit):
    deg, minute, sec = map(float, group)
    if minute >= 60 or sec >= 60 or deg > limit:
        return None
    return round(deg + minute / 60 + sec / 3600, 6)


def parse_section(code, data):
    # The source uses UTF-8. lxml otherwise guesses Latin-1 for some pages.
    document = html.fromstring(data, parser=html.HTMLParser(encoding='utf-8'))
    tables = document.xpath("//table[contains(@class,'table-ldf')]")
    if len(tables) != 1:
        raise ValueError(f'{code}: expected a light table')
    records = []
    omitted = 0
    for row in tables[0].xpath('.//tr[td]'):
        cells = row.xpath('./td')
        if len(cells) != 11:
            raise ValueError(f'{code}: light table changed')
        # A line break separates the name from a possible RACON description.
        for br in cells[1].xpath('.//br'):
            br.tail = '\n' + (br.tail or '')
        names = [' '.join(line.split()) for line in cells[1].text_content().splitlines() if line.strip()]
        ident = re.match(r'\s*(\d+(?:\.\d+)?)', text(cells[0]))
        coords = DMS.findall(text(cells[3]))
        rhythm, colour, period = (text(cells[i]) for i in (4, 5, 6))
        if not ident or not names or len(coords) != 2 or not re.search('[a-zA-Z]',rhythm) or not re.search('[a-zA-Z]',colour):
            omitted += 1
            continue
        lat, west = coordinate(coords[0], 90), coordinate(coords[1], 180)
        if lat is None or west is None:
            omitted += 1
            continue
        vol = re.match(r'[a-z]+',code)[0]
        record = {'id': f'{vol}-{ident[1]}', 'number': ident[1], 'name': names[0], 'section': code, 'lat': lat, 'lon': -west,
                  'rhythm': rhythm, 'colour': colour, 'period': number(period.removesuffix('s').strip()),
                  'height': number(text(cells[7])), 'range': number(text(cells[8]))}
        # Only reproduce alternating durations if they cover one complete, published cycle.
        phases = re.findall(r'\b(flash|eclipse)\s+(\d+(?:\.\d+)?)\s*s\b',text(cells[10]), re.I)
        if phases and len(phases)%2 == 0 and record['period']:
            durations = [float(n) for _,n in phases]
            regular = all(kind.lower() == ('flash' if i%2 == 0 else 'eclipse') for i,(kind,_) in enumerate(phases))
            if regular and min(durations)>0 and abs(sum(durations)-record['period'])<.001:
                record['durations'] = durations
        records.append(record)
    return records, omitted


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cached',type=Path,help='Directory containing index.html and original section files')
    args=parser.parse_args()
    index = sections((args.cached/'index.html').read_bytes() if args.cached else fetch(INDEX))
    def read(item):
        code, section = item
        content = (args.cached/section['url'].split('/')[-1]).read_bytes() if args.cached else fetch(section['url'])
        return parse_section(code,content)
    lights=[]; omitted=0
    with ThreadPoolExecutor(max_workers=5) as pool:
        for records, skips in pool.map(read,index.items()):
            lights.extend(records); omitted+=skips
    # The official Atlantic table currently assigns LL 110 to two different buoys.
    counts = Counter(r['id'] for r in lights)
    for record in lights:
        if counts[record['id']] > 1:
            record['id'] += '-' + sha256(record['name'].encode()).hexdigest()[:8]
    if len({r['id'] for r in lights})!=len(lights):
        raise ValueError('Duplicate volume/light identifier; review before publishing')
    target=ROOT/'web/data/lights.json'
    expected= len(json.loads(target.read_text())['lights']) if target.exists() else 3500
    if len(lights)<max(3000,expected*.9):
        raise ValueError(f'Unexpected shrinkage: {len(lights)} eligible lights')
    attribution = ('Contains information published by the Canadian Coast Guard and Department of Fisheries and Oceans '
                   'licensed under the Canadian Coast Guard Open Information Licence. This Information is available in its '
                   'original format for free download on the Canadian Coast Guard website and the Monthly Edition of the '
                   'Notices to Mariners (NOTMAR) website.')
    result={'attribution':attribution, 'licence':'https://www.canada.ca/en/canadian-coast-guard/corporate/publications/open-information-licence.html','retrieved':datetime.now(timezone.utc).date().isoformat(), 'sections':index, 'omitted':omitted,'lights':lights}
    stage=target.with_suffix('.tmp')
    stage.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    stage.replace(target)
    print(f'Saved {len(lights)} positioned light records in {len(index)} sections. Omitted {omitted} rows.')


if __name__ == '__main__':
    main()
