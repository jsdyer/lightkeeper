# Lightkeeper

<!-- coolcode:guide -->
Choose a light station and compare its character with neighbouring signals, or try Identify mode with playback started on request. Schematic flash widths are labelled when source timings are absent; use current official publications for navigation.
<!-- /coolcode:guide -->

[Open Lightkeeper](https://coolcode.ca/lightkeeper/) · [CoolCode catalogue](https://coolcode.ca/)

Find Canadian light stations and buoys by name, light number, colour or area. Choose a record on the map or in the directory to read its published character, compare neighbouring signals, and share its permalink. Identify mode offers three signals with distinct light characteristics. Playback begins on request. The timeline stays readable while paused.

## Data and interpretation

The first snapshot (November 18, 2026) indexes 6,494 positioned lights from all 66 sections of the Pacific, Atlantic, and Newfoundland and Labrador volumes of the [List of Lights, Buoys and Fog Signals](https://notmar.gc.ca/list-lights). This includes inland waters described by these volumes. The Arctic and Inland Waters volumes are outside the index. The original three volumes also contain unlit aids and rows without sufficient position or signal data. The app reports how many rows it omits. Browse by light number in each linked official section.

When source remarks give a complete sequence, the app displays the flash and eclipse durations. For example, the November 2026 snapshot lists a 1.5-second red flash and 3.5-second eclipse at Peggy's Point. The Point Atkinson entry lists two 0.25-second flashes in a five-second cycle. Isophase intervals are equal by definition. Schematic timelines are labelled, show the reported period, and illustrate the widths of the pulses when durations are absent. Complex and sector entries retain the source notation. Distances are approximate great-circle distances between published positions. Looking at a coast samples markers when more than 650 are in view; all matching records remain available in the directory. The point layer and station directory load independently of background tiles.

Use official current charts, publications, and notices for navigation. This independent educational application does not replace them.

## Source licence

Contains information published by the Canadian Coast Guard and Department of Fisheries and Oceans licensed under the [Canadian Coast Guard Open Information Licence](https://www.canada.ca/en/canadian-coast-guard/corporate/publications/open-information-licence.html). This Information is available in its original format for free download on the [Canadian Coast Guard website](https://www.canada.ca/en/canadian-coast-guard.html) and the [Monthly Edition of the Notices to Mariners (NOTMAR) website](https://notmar.gc.ca/).

The light dataset carries this attribution in its metadata. Background map tiles are from [OpenStreetMap contributors](https://www.openstreetmap.org/copyright); Leaflet's licence is in web/vendor/LICENSE. Queries and exercise answers stay in the browser. Map tile requests go to OpenStreetMap.

## Build and refresh

The committed JSON supplies the offline build. The Python standard library and Node.js suffice for the build and model tests.

```sh
node --test tests/*.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build.py
python3 -m http.server 8000 --directory dist
```

GitHub Actions exercises the built site in Chromium on desktop and mobile. Successful main builds publish dist to GitHub Pages; use the GitHub Actions source in repository Settings → Pages. Review the separate public-page and data retrieval dates in the Sources section. The catalogue can embed [the snapshot date badge](https://coolcode.ca/lightkeeper/data-date.svg).

The refresh workflow checks all volume sections twice monthly. To run the same update locally, install the parser with `python3 -m pip install -r scripts/requirements.txt`, then run `python3 scripts/refresh.py`. A failed fetch, changed table format, duplicate final identifier or drop exceeding 10% of eligible lights aborts the update. The workflow commits the validated snapshot and dispatches the normal Pages checks before publication. The coverage and correction dates come from NOTMAR; the retrieval date records when the tables were read. Within a volume the light number identifies records, with a name suffix for a duplicated number in the source.

For a saved source supplied with `--cached`, use `--retrieved-on YYYY-MM-DD` when the original acquisition date is known. An unchanged local copy preserves the recorded date. A changed local copy with unknown provenance displays “Retrieval date unrecorded.”
