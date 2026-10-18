// Undirected, unweighted simple graph. Algorithms are independent of React/D3.
export function createGraph(stations, connections) {
  const graph = new Map(stations.map(({ id }) => [id, new Set()]));
  if (graph.size !== stations.length) throw new Error("Duplicate station ID");
  const seen = new Set();
  for (const { source, target } of connections) {
    if (!graph.has(source) || !graph.has(target))
      throw new Error("Unknown station");
    if (source === target)
      throw new Error("Self-connections are not supported");
    const key = JSON.stringify([source, target].sort());
    if (seen.has(key)) throw new Error("Duplicate connection");
    seen.add(key);
    graph.get(source).add(target);
    graph.get(target).add(source);
  }
  return graph;
}

export function degreeCentrality(graph, id) {
  if (!graph.has(id)) return 0;
  return graph.size > 1 ? graph.get(id).size / (graph.size - 1) : 0;
}

// BFS returns one minimum-edge path; insertion order breaks equal-length ties.
export function shortestPath(graph, source, target) {
  if (!graph.has(source) || !graph.has(target)) return null;
  const queue = [source];
  const previous = new Map([[source, null]]);
  for (let i = 0; i < queue.length; i++) {
    const current = queue[i];
    if (current === target) {
      const path = [];
      for (let node = current; node !== null; node = previous.get(node))
        path.push(node);
      return path.reverse();
    }
    for (const neighbor of graph.get(current)) {
      if (!previous.has(neighbor)) {
        previous.set(neighbor, current);
        queue.push(neighbor);
      }
    }
  }
  return null;
}

export function connectedComponents(graph) {
  const visited = new Set();
  let count = 0;
  for (const id of graph.keys()) {
    if (visited.has(id)) continue;
    count++;
    const queue = [id];
    visited.add(id);
    for (let i = 0; i < queue.length; i++) {
      for (const neighbor of graph.get(queue[i])) {
        if (!visited.has(neighbor)) {
          visited.add(neighbor);
          queue.push(neighbor);
        }
      }
    }
  }
  return count;
}
