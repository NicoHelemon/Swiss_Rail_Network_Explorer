import { useMemo, useState } from "react";
import "./styles.css";
import { stations, connections } from "./data/network.js";
import {
  createGraph,
  degreeCentrality,
  shortestPath,
  connectedComponents,
} from "./lib/graph.js";
import NetworkMap from "./components/NetworkMap.jsx";
import Icon from "./components/Icon.jsx";

const graph = createGraph(stations, connections);
const byId = new Map(stations.map((s) => [s.id, s]));
const sortedStations = [...stations].sort((a, b) =>
  a.name.localeCompare(b.name),
);
const averageDegree = ((2 * connections.length) / stations.length).toFixed(1);
const componentCount = connectedComponents(graph);

function StationSelect({ id, label, value, onChange, variant }) {
  return (
    <div className="station-field">
      <label htmlFor={id}>
        <span className={`field-dot ${variant || ""}`} />
        {label}
      </label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
        {sortedStations.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name}
          </option>
        ))}
      </select>
    </div>
  );
}

export default function App() {
  const [selected, setSelected] = useState("zurich");
  const [source, setSource] = useState("lausanne");
  const [target, setTarget] = useState("zurich");
  const [route, setRoute] = useState(null);
  const [routeRequested, setRouteRequested] = useState(false);
  const selectedStation = byId.get(selected);
  const neighbors = useMemo(
    () =>
      [...graph.get(selected)]
        .map((id) => byId.get(id))
        .sort((a, b) => a.name.localeCompare(b.name)),
    [selected],
  );
  const centrality = degreeCentrality(graph, selected);

  function updateEndpoint(setter, value) {
    setter(value);
    setRoute(null);
    setRouteRequested(false);
  }
  function findPath(event) {
    event.preventDefault();
    setRoute(shortestPath(graph, source, target));
    setRouteRequested(true);
  }
  function clearPath() {
    setRoute(null);
    setRouteRequested(false);
  }

  return (
    <>
      <a className="skip-link" href="#explorer">
        Skip to explorer
      </a>
      <header className="site-header">
        <div className="header-inner">
          <a
            className="brand"
            href="#"
            aria-label="Swiss Rail Network Explorer home"
          >
            <span className="brand-mark">
              <Icon name="rail" size={25} />
            </span>
            <span>
              Swiss Rail<span className="brand-light"> / Network Explorer</span>
            </span>
          </a>
          <nav aria-label="Main navigation">
            <a className="nav-active" href="#explorer">
              Explorer
            </a>
            <a href="#methodology">
              Methodology <Icon name="diagonal" size={13} />
            </a>
          </nav>
          <span className="project-status">
            <span />
            Independent project · Work in progress
          </span>
        </div>
      </header>

      <main className="page-shell">
        <section className="intro" aria-labelledby="page-title">
          <div>
            <div className="eyebrow">
              <span />A STUDY IN CONNECTIVITY
            </div>
            <h1 id="page-title">
              Swiss Rail Network Explorer<span className="title-period">.</span>
            </h1>
            <p className="subtitle">
              Exploring connectivity through graph analysis
            </p>
          </div>
          <div className="intro-aside">
            <p>One network. A different perspective.</p>
            <span>
              An interactive look at the links
              <br />
              that bring Switzerland together.
            </span>
          </div>
        </section>

        <div className="demo-notice">
          <span className="demo-badge">DEMO DATA</span>
          <p>
            A simplified, synthetic network for exploring graph concepts.{" "}
            <span>No real timetable observations.</span>
          </p>
          <a href="#methodology">
            About the data <Icon name="arrow" size={15} />
          </a>
        </div>

        <section className="stats-grid" aria-label="Network statistics">
          <div className="stat">
            <div className="stat-top">
              Stations
              <Icon name="pin" size={18} />
            </div>
            <div className="stat-value">
              {stations.length}
              <span>nodes</span>
            </div>
            <p>Major stations in this demo</p>
          </div>
          <div className="stat">
            <div className="stat-top">
              Connections
              <Icon name="network" size={19} />
            </div>
            <div className="stat-value">
              {connections.length}
              <span>edges</span>
            </div>
            <p>Undirected, unweighted links</p>
          </div>
          <div className="stat">
            <div className="stat-top">
              Average degree
              <Icon name="link" size={18} />
            </div>
            <div className="stat-value">
              {averageDegree}
              <span>links / station</span>
            </div>
            <p>Mean number of direct connections</p>
          </div>
          <div className="stat">
            <div className="stat-top">
              Connected components
              <Icon name="network" size={19} />
            </div>
            <div className="stat-value">
              {componentCount}
              <span className="connected-tag">
                <span />
                {componentCount === 1 ? "Fully connected" : "Separate groups"}
              </span>
            </div>
            <p>
              {componentCount === 1
                ? "Every station is reachable"
                : "Some stations are disconnected"}
            </p>
          </div>
        </section>

        <section
          id="explorer"
          className="explorer-section"
          aria-label="Network explorer"
        >
          <div className="section-heading">
            <h2>
              <span>01</span> Explore the connections
            </h2>
            <span className="section-caption">
              A topological view of Switzerland
            </span>
          </div>
          <div className="explorer-grid">
            <NetworkMap
              stations={stations}
              connections={connections}
              graph={graph}
              selected={selected}
              onSelect={setSelected}
              path={route}
              clearPath={clearPath}
            />
            <aside
              className="explorer-sidebar"
              aria-label="Network analysis tools"
            >
              <section
                className="panel route-panel"
                aria-labelledby="route-title"
              >
                <div className="panel-heading">
                  <span className="panel-icon">
                    <Icon name="network" size={18} />
                  </span>
                  <h3 id="route-title">Find a connection</h3>
                </div>
                <p className="panel-description">
                  Two stations. The fewest links between them.
                </p>
                <form onSubmit={findPath}>
                  <div className="route-fields">
                    <StationSelect
                      id="from-station"
                      label="From"
                      value={source}
                      onChange={(v) => updateEndpoint(setSource, v)}
                    />
                    <button
                      className="swap-button"
                      type="button"
                      aria-label="Swap origin and destination"
                      onClick={() => {
                        setSource(target);
                        setTarget(source);
                        clearPath();
                      }}
                    >
                      <Icon name="swap" size={15} />
                    </button>
                    <StationSelect
                      id="to-station"
                      label="To"
                      value={target}
                      onChange={(v) => updateEndpoint(setTarget, v)}
                      variant="destination"
                    />
                  </div>
                  <button type="submit" className="primary-button">
                    Find shortest path <Icon name="arrow" size={17} />
                  </button>
                </form>
                <div className="route-result" aria-live="polite">
                  {routeRequested ? (
                    route ? (
                      <>
                        <div className="route-result-heading">
                          <span className="result-dot" />
                          <strong>
                            {route.length - 1}{" "}
                            {route.length === 2 ? "connection" : "connections"}
                          </strong>
                          <span>
                            {route.length}{" "}
                            {route.length === 1 ? "station" : "stations"}
                          </span>
                        </div>
                        <p className="route-sequence">
                          {route.map((id, i) => (
                            <span key={id}>
                              {i > 0 && <Icon name="chevron" size={11} />}
                              <button onClick={() => setSelected(id)}>
                                {byId.get(id).name}
                              </button>
                            </span>
                          ))}
                        </p>
                        {route.length === 1 && (
                          <p className="same-station">
                            You’re already there. Choose another destination to
                            explore.
                          </p>
                        )}
                        <button
                          className="text-button clear-result"
                          onClick={clearPath}
                        >
                          Clear path <Icon name="close" size={12} />
                        </button>
                      </>
                    ) : (
                      <p>No path connects these stations in this network.</p>
                    )
                  ) : (
                    <p className="route-help">
                      <Icon name="info" size={14} />
                      Fewest edges, not the fastest journey.
                    </p>
                  )}
                </div>
              </section>

              <section
                className="panel station-panel"
                aria-labelledby="station-title"
              >
                <div className="station-eyebrow">
                  STATION SPOTLIGHT
                  <span className="selection-label">Selected</span>
                </div>
                <div className="station-title-row">
                  <h3 id="station-title">{selectedStation.name}</h3>
                  <Icon name="pin" size={21} />
                </div>
                <div className="station-metrics">
                  <div>
                    <strong>{neighbors.length}</strong>
                    <span>Direct connections</span>
                  </div>
                  <div>
                    <strong>{centrality.toFixed(3)}</strong>
                    <span>Degree centrality</span>
                  </div>
                </div>
                <div
                  className="centrality-track"
                  role="meter"
                  aria-label="Normalized degree centrality"
                  aria-valuenow={centrality}
                  aria-valuemin={0}
                  aria-valuemax={1}
                >
                  <span style={{ width: `${centrality * 100}%` }} />
                </div>
                <p className="centrality-explanation">
                  Connected to <strong>{(centrality * 100).toFixed(1)}%</strong>{" "}
                  of the other stations in this graph.
                </p>
                <div className="neighbor-heading">
                  CONNECTED STATIONS{" "}
                  <span>{neighbors.length.toString().padStart(2, "0")}</span>
                </div>
                <div className="neighbor-list">
                  {neighbors.map((s) => (
                    <button key={s.id} onClick={() => setSelected(s.id)}>
                      {s.name}
                      <Icon name="diagonal" size={12} />
                    </button>
                  ))}
                </div>
                <p className="station-footnote">
                  Select any station on the map to inspect it.
                </p>
              </section>
            </aside>
          </div>
        </section>

        <section
          className="metric-guide"
          aria-label="Understanding the metrics"
        >
          <div className="guide-title">
            <Icon name="info" size={18} />
            <h2>Reading the network</h2>
          </div>
          <div>
            <h3>Degree centrality</h3>
            <p>
              Direct connections divided by all other stations:{" "}
              <code>degree / (N − 1)</code>. A measure of local connectivity
              within this graph.
            </p>
          </div>
          <div>
            <h3>Shortest path</h3>
            <p>
              The route with the fewest edges, found using breadth-first search.
              Equal-length alternatives may exist; one is shown.
            </p>
          </div>
          <div>
            <h3>Topology ≠ operations</h3>
            <p>
              These links say nothing about capacity, delays, service frequency,
              or journey time. High connectivity alone does not imply a
              bottleneck.
            </p>
          </div>
        </section>

        <section
          id="methodology"
          className="methodology"
          aria-labelledby="about-title"
        >
          <div className="section-heading">
            <h2>
              <span>02</span> Beyond the diagram
            </h2>
            <span className="section-caption">Purpose & methodology</span>
          </div>
          <div className="about-grid">
            <div className="about-intro">
              <span className="eyebrow">A PERSONAL EXPLORATION</span>
              <h2 id="about-title">
                Small graph.
                <br />
                Bigger questions.
              </h2>
              <p>
                How do individual connections shape a network? This independent
                project explores that question through the lens of Swiss rail.
              </p>
              <p>
                Built by an EPFL MSc graduate interested in data science, graph
                theory, and railway planning. A working proof of concept,
                designed to grow.
              </p>
              <a
                className="portal-link"
                href="https://opentransportdata.swiss/en/"
                target="_blank"
                rel="noreferrer"
              >
                Swiss public transport open data{" "}
                <Icon name="diagonal" size={16} />
              </a>
            </div>
            <div className="method-cards">
              <article>
                <span className="method-number">01 / MODEL</span>
                <h3>Intentionally simplified</h3>
                <p>
                  {stations.length} stations, {connections.length} illustrative
                  links. An undirected, unweighted simple graph with schematic
                  positions. Connections are hand-authored for demonstration and
                  do not assert direct train services. All metrics use this
                  exact graph.
                </p>
              </article>
              <article>
                <span className="method-number">02 / POSSIBILITIES</span>
                <h3>From connections to decisions</h3>
                <p>
                  Graph analysis can help frame questions about accessibility
                  and network structure. Timetable planning needs more: actual
                  schedules, demand, infrastructure, and operational
                  constraints.
                </p>
              </article>
              <article className="next-step">
                <span className="method-number">03 / WHAT’S NEXT</span>
                <h3>
                  A foundation for real data <Icon name="diagonal" size={17} />
                </h3>
                <p>
                  Replace the demo with GTFS schedules from
                  opentransportdata.swiss. Add service frequencies,
                  time-dependent paths, and temporal network analysis.
                </p>
                <div className="future-tags">
                  <span>GTFS schedules</span>
                  <span>Service frequencies</span>
                  <span>Temporal networks</span>
                </div>
              </article>
            </div>
          </div>
        </section>
        <footer className="site-footer">
          <div>
            <span className="footer-mark">
              <Icon name="rail" size={18} />
            </span>
            <span>
              Swiss Rail Network Explorer
              <span className="footer-divider">/</span>
              <span className="footer-muted">Made with curiosity.</span>
            </span>
          </div>
          <p>
            Independent portfolio project. Not affiliated with SBB or any
            transport operator.
          </p>
        </footer>
      </main>
    </>
  );
}
