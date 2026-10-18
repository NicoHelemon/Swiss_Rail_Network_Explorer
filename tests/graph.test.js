import test from "node:test";
import assert from "node:assert/strict";
import {
  createGraph,
  degreeCentrality,
  shortestPath,
  connectedComponents,
} from "../src/lib/graph.js";
import { stations, connections } from "../src/data/network.js";

const graph = createGraph(stations, connections);

test("demo data forms one undirected simple graph with all displayed links", () => {
  assert.equal(graph.size, 20);
  assert.equal(connections.length, 27);
  assert.equal(connectedComponents(graph), 1);
  assert.equal(
    [...graph.values()].reduce((sum, neighbors) => sum + neighbors.size, 0),
    54,
  );
  for (const edge of connections) {
    assert.ok(graph.get(edge.source).has(edge.target));
    assert.ok(graph.get(edge.target).has(edge.source));
  }
});

test("degree centrality is computed from displayed neighbors and graph size", () => {
  assert.equal(graph.get("zurich").size, 7);
  assert.equal(degreeCentrality(graph, "zurich"), 7 / 19);
  assert.equal(degreeCentrality(graph, "geneve"), 1 / 19);
});

test("BFS finds a minimum-edge route in both directions", () => {
  const path = shortestPath(graph, "geneve", "lugano");
  assert.equal(path.length - 1, 8);
  assert.equal(path[0], "geneve");
  assert.equal(path.at(-1), "lugano");
  for (let i = 1; i < path.length; i++)
    assert.ok(graph.get(path[i - 1]).has(path[i]));
  assert.equal(shortestPath(graph, "lugano", "geneve").length, path.length);
  assert.equal(shortestPath(graph, "lausanne", "zurich").length - 1, 4);
});

test("same station is a zero-edge path; unknown endpoints have no path", () => {
  assert.deepEqual(shortestPath(graph, "bern", "bern"), ["bern"]);
  assert.equal(shortestPath(graph, "missing", "bern"), null);
  assert.equal(shortestPath(graph, "bern", "missing"), null);
});

test("disconnected and singleton graphs are handled", () => {
  const isolated = createGraph(
    [{ id: "a" }, { id: "b" }, { id: "c" }],
    [{ source: "a", target: "b" }],
  );
  assert.equal(shortestPath(isolated, "a", "c"), null);
  assert.equal(connectedComponents(isolated), 2);
  assert.equal(degreeCentrality(createGraph([{ id: "a" }], []), "a"), 0);
  assert.equal(connectedComponents(new Map()), 0);
});

test("invalid graph data fails explicitly", () => {
  const nodes = [{ id: "a" }, { id: "b" }];
  assert.throws(
    () => createGraph(nodes, [{ source: "a", target: "c" }]),
    /Unknown/,
  );
  assert.throws(
    () => createGraph(nodes, [{ source: "a", target: "a" }]),
    /Self/,
  );
  assert.throws(
    () =>
      createGraph(nodes, [
        { source: "a", target: "b" },
        { source: "b", target: "a" },
      ]),
    /Duplicate/,
  );
  assert.throws(() => createGraph([{ id: "a" }, { id: "a" }], []), /Duplicate/);
});
