# Swiss Rail Network Explorer

V2 research is being prepared as **Swiss Rail Delay Lab**. The official catalogue and documentation are accessible; CSV downloads redirect to an additional storage host whose cloud network access is pending. No observation files, real-data findings, or predictive results are available yet. The working V1 below remains unchanged. See [the feasibility checkpoint](docs/data_feasibility.md) and [provisional research protocol](docs/research_protocol.md). Source-audit parser tests: `python -m unittest research.test_audit_source`. These tests use synthetic fixtures and do not validate official records.

**Exploring connectivity through graph analysis.** An independent portfolio project by an EPFL MSc graduate interested in data science, graph theory, and railway planning. Not affiliated with SBB, EPFL, or any transport operator.

A small, static React application: explore a schematic network, inspect station connectivity, and highlight minimum-edge paths. Built with Vite, React, D3 zoom/selection, and plain CSS. No backend, API key, authentication, or environment variables are required. Fonts are bundled locally; the application makes no external data requests.

## Run locally

Use Node.js 24 LTS (`.nvmrc`; minimum 22.12).

```sh
npm ci
npm run dev
```

Open the address printed by Vite. To validate and preview the production version:

```sh
npm test
npm run build
npm run preview
```

If your environment restricts writes to your home directory, append `--cache /workspace/.cache/npm` to `npm ci`. Build output is in `dist/` and is intentionally ignored by Git.

## Explore

- Click or tap a station to inspect its degree, normalized degree centrality, and neighbors. Neighbor chips also select stations.
- Choose an origin and destination, then select **Find shortest path**. Highlighted red edges show one minimum-edge route. Changing either endpoint clears the previous result; the swap button reverses the endpoints.
- Scroll/pinch to zoom, drag the canvas to pan, or use the zoom/reset buttons. Clear the path to return to the station-neighborhood view.
- Stations are keyboard focusable. Press Enter or Space to select one; form controls and map buttons support standard keyboard navigation. Use the origin/destination dropdowns as an alternative to selecting small map targets on mobile.

## Data and methodology

**All network links are synthetic/demo data, not actual timetable observations.** The names refer to real stations, but the 27 hand-authored links between 20 stations do not establish direct train services. Positions are schematic, not geographic. This is a deliberately small, undirected, unweighted simple graph, with no parallel edges or self-loops.

Every displayed metric uses the exact same nodes and edges drawn on the map:

| Metric                       | Definition                                       | Demo value                    |
| ---------------------------- | ------------------------------------------------ | ----------------------------- |
| Stations                     | Number of nodes, N                               | 20                            |
| Connections                  | Number of undirected edges, E; each counted once | 27                            |
| Average degree               | 2E / N                                           | 2.7                           |
| Connected components         | Number of maximal connected node groups          | 1                             |
| Degree                       | Number of distinct direct neighbors of a station | Depends on selection          |
| Normalized degree centrality | degree / (N − 1); zero for a singleton           | Zürich HB: 7 / 19 ≈ 0.368     |
| Shortest path                | Breadth-first search, minimizing edge count      | Lausanne → Zürich HB: 4 edges |

BFS takes O(N + E) time and O(N) auxiliary space. If several shortest paths exist, the app displays one, using dataset insertion order to resolve ties. Identical origin/destination returns one station and zero edges; disconnected or unknown endpoints return no path. The test suite includes these edge cases.

These topological measures **do not identify operational bottlenecks**. They do not account for service frequency, train capacity, infrastructure, demand, delays, transfer feasibility, or travel time. A high-degree node has many connections in this demo, which does not establish its real-world importance or congestion. A minimum-edge path is not necessarily a fastest journey or even a feasible scheduled itinerary.

## Replace the demo with GTFS

Data lives in `src/data/network.js`, separate from graph algorithms (`src/lib/graph.js`) and presentation. A future import process can generate static data with the same contract:

```js
stations = [
  { id: "stable-station-id", name: "Station", x: 100, y: 200, label: "bottom" },
];
connections = [
  { id: "stable-edge-id", source: "station-a", target: "station-b" },
];
```

Station IDs must be unique, edge endpoints must exist, and edge IDs must use `[source, target].sort().join('--')`, matching path highlighting. `createGraph` validates unknown endpoints, duplicate connections, duplicate station IDs, and self-loops. `label` accepts `top`, `bottom`, `left`, or `right`; x/y positions use the 1020 × 650 schematic coordinate system. Keep the dataset metadata and visible data labels consistent with any future source.

Start with the [Swiss public transport open data portal](https://opentransportdata.swiss/en/). A useful next iteration would:

1. Download an official GTFS release, recording its provenance, date, license, and service window.
2. Group platform-level stops into stations using `stops.txt` and parent relationships. Filter the intended rail services through `routes.txt` and `trips.txt`.
3. Derive edges from consecutive stops in `stop_times.txt`, document whether skipped stops represent direct service links or physical infrastructure, and deduplicate accordingly. Scheduled service data alone is not a track-infrastructure graph.
4. Add service frequencies with calendar validity (`calendar.txt` / `calendar_dates.txt`), then direction, transfer rules, and time-dependent routing as separate models.

Perform ingestion at build time or in an offline script to keep the deployed application static. Authentic schedules are much larger than this demo: choose a documented subset before rendering. Timetable planning and temporal network analysis require a richer model than this unweighted proof of concept.

## Deploy on Netlify

### From Git (recommended)

Push this project to your GitHub repository. In Netlify, select **Add new project → Import an existing project**, connect the repository, and deploy. `netlify.toml` already sets:

- Build command: `npm run build`
- Publish directory: `dist`
- Node version: `24`

If Netlify asks for a base directory, leave it empty when these files are at the repository root. No secrets or runtime configuration are needed. The application uses anchor links, so no SPA redirect rule is required.

### Fastest manual deployment

Run `npm ci && npm run build`, then drag the **dist folder** into [Netlify Drop](https://app.netlify.com/drop). The folder's top level must contain `index.html`. This uploads the compiled application, not the source. Build settings/headers in `netlify.toml` apply to Git-based builds; Drop simply hosts the generated files.

### With an authenticated CLI

```sh
npx netlify-cli deploy --prod --dir=dist
```

For a new site, follow the CLI's site-creation prompts. The cloud development environment does not include a configured Netlify account, so no public deployment is assumed or claimed by this project.

## Project structure

```text
src/
  App.jsx                    State, analytics panels, methodology
  components/NetworkMap.jsx  SVG network and D3 zoom/pan
  components/Icon.jsx        Small original UI icons
  data/network.js            Replaceable synthetic dataset
  lib/graph.js               Pure graph algorithms
  styles.css                 Responsive styling
tests/graph.test.js           Node's built-in test runner
netlify.toml                 Build and hosting configuration
```

Dependencies are locked in `package-lock.json`. Fonts are distributed under their bundled OFL licenses in the Fontsource packages. The station/rail icons are original geometric UI marks, not official SBB branding.
