import { useEffect, useRef, useState } from "react";
import { select } from "d3-selection";
import { zoom, zoomIdentity } from "d3-zoom";
import Icon from "./Icon.jsx";

export default function NetworkMap({
  stations,
  connections,
  graph,
  selected,
  onSelect,
  path,
  clearPath,
}) {
  const svgRef = useRef(null);
  const zoomRef = useRef(null);
  const [scale, setScale] = useState(1);
  const [hovered, setHovered] = useState(null);
  const [transform, setTransform] = useState("translate(0,0) scale(1)");
  const byId = new Map(stations.map((s) => [s.id, s]));
  const pathNodes = new Set(path || []);
  const pathEdges = new Set(
    (path || []).slice(1).map((id, i) => [path[i], id].sort().join("--")),
  );
  const neighborIds = graph.get(selected) || new Set();

  useEffect(() => {
    const element = select(svgRef.current);
    const behavior = zoom()
      .scaleExtent([0.7, 3.5])
      .extent([
        [0, 0],
        [1020, 650],
      ])
      .translateExtent([
        [-350, -250],
        [1370, 900],
      ])
      .filter(
        (event) =>
          (!event.ctrlKey || event.type === "wheel") &&
          !event.button &&
          !event.target.closest("[data-station]"),
      )
      .on("zoom", (event) => {
        setTransform(event.transform.toString());
        setScale(event.transform.k);
      });
    element.call(behavior);
    zoomRef.current = behavior;
    return () => {
      element.on(".zoom", null);
    };
  }, []);

  function changeZoom(factor) {
    select(svgRef.current).call(zoomRef.current.scaleBy, factor);
  }

  function reset() {
    select(svgRef.current).call(zoomRef.current.transform, zoomIdentity);
  }

  const hoveredStation = byId.get(hovered);
  return (
    <section className="map-card" aria-labelledby="map-title">
      <div className="map-toolbar">
        <div>
          <span className="live-dot" />
          <h2 id="map-title">The network</h2>
          <span className="schematic-tag">Schematic view</span>
        </div>
        <span className="map-index">CH — 01</span>
      </div>
      <div className="map-stage">
        <div className="map-note">
          <span className="tiny-cross">+</span> A small network. Many
          connections.
          <span>Select a station to explore its neighbourhood.</span>
        </div>
        <svg
          ref={svgRef}
          className="network-svg"
          viewBox="0 0 1020 650"
          role="group"
          aria-label="Interactive schematic railway network. Use Tab to reach stations, Enter to select, and the buttons to zoom."
        >
          <defs>
            <pattern
              id="dots"
              width="22"
              height="22"
              patternUnits="userSpaceOnUse"
            >
              <circle cx="1" cy="1" r="0.8" fill="#e2e5e4" />
            </pattern>
            <filter
              id="station-shadow"
              x="-100%"
              y="-100%"
              width="300%"
              height="300%"
            >
              <feDropShadow
                dx="0"
                dy="2"
                stdDeviation="3"
                floodOpacity="0.12"
              />
            </filter>
          </defs>
          <rect width="1020" height="650" fill="url(#dots)" />
          <g transform={transform}>
            <text x="60" y="110" className="map-region">
              FRANCE
            </text>
            <text x="820" y="45" className="map-region">
              GERMANY
            </text>
            <text x="890" y="570" className="map-region">
              ITALY
            </text>
            <path
              d="M230 460q45 25 80-5t80 0 90 20 90 0 100 10"
              className="alpine-line"
            />
            <text x="375" y="488" className="alps-label">
              S W I S S A L P S
            </text>
            {connections.map((edge) => {
              const source = byId.get(edge.source),
                target = byId.get(edge.target);
              const active = pathEdges.has(edge.id);
              const adjacent =
                edge.source === selected || edge.target === selected;
              return (
                <line
                  key={edge.id}
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  className={`network-edge ${active ? "path-edge" : ""} ${!path && adjacent ? "neighbor-edge" : ""} ${path && !active ? "muted-edge" : ""}`}
                  data-edge={edge.id}
                  data-highlighted={active}
                />
              );
            })}
            {stations.map((station) => {
              const isSelected = selected === station.id;
              const inPath = pathNodes.has(station.id);
              const isNeighbor = neighborIds.has(station.id);
              const offsets = {
                top: [0, -20, "middle"],
                bottom: [0, 28, "middle"],
                left: [-18, 5, "end"],
                right: [18, 5, "start"],
              };
              const [dx, dy, anchor] = offsets[station.label];
              return (
                <g
                  key={station.id}
                  transform={`translate(${station.x},${station.y})`}
                  className={`station ${isSelected ? "is-selected" : ""} ${inPath ? "in-path" : ""} ${!path && isNeighbor ? "is-neighbor" : ""} ${path && !inPath && !isSelected ? "muted-station" : ""}`}
                  role="button"
                  tabIndex={0}
                  aria-label={`${station.name}, ${graph.get(station.id).size} connections`}
                  aria-pressed={isSelected}
                  data-station={station.id}
                  onClick={() => onSelect(station.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onSelect(station.id);
                    }
                  }}
                  onMouseEnter={() => setHovered(station.id)}
                  onMouseLeave={() => setHovered(null)}
                  onFocus={() => setHovered(station.id)}
                  onBlur={() => setHovered(null)}
                >
                  <title>
                    {station.name} · {graph.get(station.id).size} direct
                    connections in this demo
                  </title>
                  <circle className="station-hit" r="17" />
                  {isSelected && <circle className="selection-halo" r="18" />}
                  <circle className="station-dot" r={isSelected ? 8 : 6} />
                  {isSelected && <circle r="2.5" fill="white" />}
                  <text
                    x={dx}
                    y={dy}
                    textAnchor={anchor}
                    className="station-label"
                  >
                    {station.name}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>
        {hoveredStation && (
          <div className="map-hover" role="status">
            <strong>{hoveredStation.name}</strong>
            <span>
              {graph.get(hovered).size} direct connections · Select to inspect
            </span>
          </div>
        )}
        <div className="orientation" aria-hidden="true">
          <span>N</span>
          <span>↑</span>
        </div>
        <div className="zoom-controls">
          <button onClick={() => changeZoom(1.25)} aria-label="Zoom in">
            <Icon name="plus" size={18} />
          </button>
          <span aria-live="polite">{Math.round(scale * 100)}%</span>
          <button onClick={() => changeZoom(0.8)} aria-label="Zoom out">
            <Icon name="minus" size={18} />
          </button>
          <span className="control-divider" />
          <button onClick={reset} aria-label="Reset map view">
            <Icon name="reset" size={17} />
          </button>
        </div>
        {path && (
          <button className="clear-map-path" onClick={clearPath}>
            <Icon name="close" size={13} />
            Clear path
          </button>
        )}
      </div>
      <div className="map-footer">
        <div className="legend">
          <span>
            <i className="legend-node" />
            Station
          </span>
          <span>
            <i className="legend-line" />
            Connection
          </span>
          <span>
            <i className="legend-line red" />
            {path ? "Selected path" : "Selected connections"}
          </span>
        </div>
        <span className="map-hint">Scroll to zoom · Drag to pan</span>
      </div>
    </section>
  );
}
