// Adapter boundary: replace these nodes/edges with normalized GTFS-derived data.
// Coordinates are schematic presentation data, never geographic measurements.
export const metadata = {
  name: "Swiss railway demo",
  kind: "synthetic",
  directed: false,
  weighted: false,
};

export const stations = [
  { id: "geneve", name: "Genève", x: 85, y: 440, label: "bottom" },
  { id: "lausanne", name: "Lausanne", x: 210, y: 390, label: "bottom" },
  { id: "neuchatel", name: "Neuchâtel", x: 245, y: 275, label: "left" },
  { id: "biel", name: "Biel/Bienne", x: 350, y: 230, label: "top" },
  { id: "fribourg", name: "Fribourg", x: 305, y: 365, label: "bottom" },
  { id: "bern", name: "Bern", x: 410, y: 330, label: "left" },
  { id: "basel", name: "Basel SBB", x: 455, y: 105, label: "top" },
  { id: "olten", name: "Olten", x: 520, y: 230, label: "bottom" },
  { id: "luzern", name: "Luzern", x: 605, y: 340, label: "left" },
  { id: "zurich", name: "Zürich HB", x: 680, y: 210, label: "bottom" },
  { id: "winterthur", name: "Winterthur", x: 785, y: 165, label: "top" },
  { id: "schaffhausen", name: "Schaffhausen", x: 725, y: 70, label: "top" },
  { id: "stgallen", name: "St. Gallen", x: 925, y: 220, label: "bottom" },
  { id: "chur", name: "Chur", x: 890, y: 380, label: "right" },
  { id: "arth", name: "Arth-Goldau", x: 700, y: 370, label: "right" },
  { id: "bellinzona", name: "Bellinzona", x: 725, y: 505, label: "right" },
  { id: "lugano", name: "Lugano", x: 725, y: 580, label: "right" },
  { id: "interlaken", name: "Interlaken Ost", x: 495, y: 430, label: "right" },
  { id: "brig", name: "Brig", x: 510, y: 530, label: "bottom" },
  { id: "sion", name: "Sion", x: 345, y: 530, label: "bottom" },
];

const links = [
  ["geneve", "lausanne"],
  ["lausanne", "neuchatel"],
  ["lausanne", "fribourg"],
  ["lausanne", "sion"],
  ["neuchatel", "biel"],
  ["biel", "bern"],
  ["biel", "olten"],
  ["fribourg", "bern"],
  ["basel", "olten"],
  ["basel", "zurich"],
  ["olten", "bern"],
  ["olten", "zurich"],
  ["olten", "luzern"],
  ["bern", "interlaken"],
  ["bern", "brig"],
  ["luzern", "zurich"],
  ["luzern", "arth"],
  ["zurich", "arth"],
  ["zurich", "chur"],
  ["zurich", "winterthur"],
  ["zurich", "schaffhausen"],
  ["winterthur", "schaffhausen"],
  ["winterthur", "stgallen"],
  ["stgallen", "chur"],
  ["arth", "bellinzona"],
  ["bellinzona", "lugano"],
  ["sion", "brig"],
];

export const connections = links.map(([source, target]) => ({
  id: [source, target].sort().join("--"),
  source,
  target,
}));
