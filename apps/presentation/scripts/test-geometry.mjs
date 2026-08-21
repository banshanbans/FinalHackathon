import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

import {
  automakerMapTrackPoints,
  featurePath,
  featureRepresentativePoint,
  interactionCurve,
  pathAtProgress,
  pointAtPathProgress,
  polylineSvgPath,
  pointInFeature,
  provinceAnchorMap,
  projectMercator,
} from "../src/presentationGeometry.ts";
import { mapViewLockReason, resolveMapView } from "../src/presentationView.ts";
import { heightMetersForValue, normalizedHeight } from "../src/presentationHeight.ts";

const collection = JSON.parse(await readFile(
  new URL("../public/assets/china-causal-map.geojson", import.meta.url),
  "utf8",
));
const standardMap = await readFile(
  new URL("../public/assets/china-standard-map.svg", import.meta.url),
  "utf8",
);
const southChinaSeaOverlay = await readFile(
  new URL("../public/assets/china-south-sea-standard-overlay.svg", import.meta.url),
  "utf8",
);
const southChinaSeaDashes = await readFile(
  new URL("../public/assets/china-south-sea-standard-dashes.svg", import.meta.url),
  "utf8",
);
const southChinaSeaDashesGeojson = JSON.parse(await readFile(
  new URL("../public/assets/china-south-sea-standard-dashes.geojson", import.meta.url),
  "utf8",
));
const southChinaSeaInset = await readFile(
  new URL("../src/SouthChinaSeaInset.tsx", import.meta.url),
  "utf8",
);
const presentationMap = await readFile(
  new URL("../src/PresentationMap.tsx", import.meta.url),
  "utf8",
);
const presentationMapFallback = await readFile(
  new URL("../src/PresentationMapFallback.tsx", import.meta.url),
  "utf8",
);
const presentationCss = await readFile(
  new URL("../src/presentation.css", import.meta.url),
  "utf8",
);
assert.match(standardMap, /GS2016-1609/, "official standard-map source for the South China Sea inset missing");
assert.match(southChinaSeaOverlay, /MNR-standard-map-GS2016-1609/, "derived South China Sea map provenance missing");
assert.match(southChinaSeaOverlay, /black-cartographic-ink-crop/, "South China Sea overlay derivation missing");
assert.ok(
  (southChinaSeaOverlay.match(/<path\b/g) ?? []).length >= 10,
  "South China Sea overlay must retain the standard cartographic ink",
);
assert.match(southChinaSeaDashes, /MNR-standard-map-GS2016-1609/, "South China Sea dash provenance missing");
assert.match(
  southChinaSeaDashes,
  /data-layer="south-china-sea-discontinuous-line"/,
  "South China Sea discontinuous-line layer missing",
);
assert.ok(
  (southChinaSeaDashes.match(/<line\b/g) ?? []).length === 12,
  "South China Sea discontinuous line must derive 12 slender segments from the official symbols",
);
assert.equal(southChinaSeaDashesGeojson.metadata.map_source, "MNR-standard-map-GS2016-1609");
assert.equal(southChinaSeaDashesGeojson.metadata.path_count, 46);
assert.equal(southChinaSeaDashesGeojson.metadata.segment_count, 12);
assert.equal(southChinaSeaDashesGeojson.metadata.simulation_scope, "none");
assert.deepEqual(southChinaSeaDashesGeojson.metadata.display_bounds, [106, 6, 127.5, 26]);
assert.ok(
  southChinaSeaDashesGeojson.features.every((feature) => feature.geometry.type === "LineString"),
  "South China Sea boundary must render as slender lines rather than filled glyph polygons",
);
assert.match(southChinaSeaInset, /MNR-standard-map-GS2016-1609/, "South China Sea inset provenance missing");
assert.match(
  southChinaSeaInset,
  /data-positioning="map-viewport-fixed"/,
  "South China Sea inset must stay fixed to the map viewport",
);
assert.match(
  southChinaSeaInset,
  /china-south-sea-standard-overlay\.svg/,
  "South China Sea map must use the transparent standard-map overlay",
);
assert.match(
  southChinaSeaInset,
  /SOUTH_CHINA_SEA_BOUNDARY_CORNERS/,
  "South China Sea discontinuous line must define one shared cartographic placement",
);
assert.match(southChinaSeaInset, /<figcaption>南海诸岛<\/figcaption>/, "standard South China Sea label missing");
assert.match(
  presentationCss,
  /\.south-china-sea-inset\s*\{[^}]*border:\s*1px dashed/s,
  "South China Sea inset must use the standard dashed frame",
);
assert.match(
  presentationCss,
  /\.south-china-sea-inset\s*\{[^}]*position:\s*absolute;[^}]*left:\s*320px;[^}]*bottom:\s*148px/s,
  "South China Sea inset must be fixed to the lower-left map viewport",
);
assert.doesNotMatch(
  presentationCss,
  /\.split-compare-stage \.south-china-sea-inset/,
  "South China Sea inset must not follow branch or camera layouts",
);
assert.doesNotMatch(
  presentationCss,
  /\.south-china-sea-map-dashes\s*\{/,
  "South China Sea discontinuous line must not remain a screen-fixed CSS overlay",
);
assert.match(
  presentationMap,
  /addSource\("south-china-sea-boundary",\s*\{[^}]*type:\s*"geojson"[^}]*data:\s*SOUTH_CHINA_SEA_BOUNDARY_GEOJSON_URL/s,
  "WebGL map must georeference the official discontinuous-line asset",
);
assert.match(
  presentationMap,
  /positioning:\s*"map-georeferenced"/,
  "WebGL discontinuous line must share the national-map camera",
);
assert.match(
  presentationMapFallback,
  /className="fallback-south-china-sea-boundary"[\s\S]*data-positioning="map-georeferenced"/,
  "SVG fallback must place the official discontinuous line inside the geography transform",
);
assert.match(
  presentationCss,
  /\.south-china-sea-inset\s*\{[^}]*background:\s*transparent;[^}]*box-shadow:\s*none/s,
  "South China Sea inset must render as map content rather than an annotation card",
);
const simulationFeatures = collection.features.filter(
  (feature) => feature.properties.included_in_simulation,
);
assert.equal(simulationFeatures.length, 31, "Presentation map must retain all 31 simulation provinces");
assert.equal(collection.metadata.non_overlapping_render_surfaces, true);

for (const feature of simulationFeatures) {
  const anchor = featureRepresentativePoint(feature);
  assert.equal(
    pointInFeature(anchor, feature),
    true,
    `${feature.properties.name} anchor must remain inside its province geometry`,
  );
  assert.match(featurePath(feature, collection.bbox), /^M/, `${feature.properties.name} SVG path missing`);
}

const [west, south, east, north] = collection.bbox;
assert.deepEqual(projectMercator([west, north], collection.bbox), [0, 0]);
assert.deepEqual(projectMercator([east, south], collection.bbox), [1000, 720]);
assert.deepEqual(projectMercator([west, south], collection.bbox), [0, 720]);
assert.deepEqual(projectMercator([east, north], collection.bbox), [1000, 0]);

const provinceAnchors = provinceAnchorMap(collection);
const automakerAnchors = automakerMapTrackPoints(["changan", "chery", "sgmw"], provinceAnchors);
const chongqingAnchor = provinceAnchors.get("50");
const anhuiAnchor = provinceAnchors.get("34");
const guangxiAnchor = provinceAnchors.get("45");
assert.deepEqual(automakerAnchors.get("changan"), [chongqingAnchor[0] - 0.2, chongqingAnchor[1] + 0.14]);
assert.deepEqual(automakerAnchors.get("chery"), [anhuiAnchor[0] + 0.24, anhuiAnchor[1] - 0.16]);
assert.deepEqual(automakerAnchors.get("sgmw"), guangxiAnchor);
for (const point of automakerAnchors.values()) {
  assert.ok(point[0] >= west && point[0] <= east, "automaker rail longitude must stay in map bounds");
  assert.ok(point[1] >= south && point[1] <= north, "automaker rail latitude must stay in map bounds");
}

const curve = interactionCurve([100, 30], [112, 36], 2);
assert.deepEqual(curve, interactionCurve([100, 30], [112, 36], 2), "curve sampling must be deterministic");
assert.deepEqual(curve[0], [100, 30]);
assert.deepEqual(curve.at(-1), [112, 36]);
for (const progress of [0.1, 0.35, 0.72, 1]) {
  const partial = pathAtProgress(curve, progress);
  const expected = pointAtPathProgress(curve, progress);
  const actual = partial.at(-1);
  assert.ok(Math.abs(actual[0] - expected[0]) < 1e-9);
  assert.ok(Math.abs(actual[1] - expected[1]) < 1e-9);
}
assert.match(polylineSvgPath(curve), /^M100\.00,30\.00 L/, "SVG must consume the shared samples");

const interactionContext = {
  frameKind: "wave",
  branchView: "treatment",
  hasSpotlight: true,
};
assert.equal(resolveMapView({ ...interactionContext, preference: "auto", activeBeat: 2 }), "top");
assert.equal(resolveMapView({ ...interactionContext, preference: "auto", activeBeat: 3 }), "side");
assert.equal(resolveMapView({ ...interactionContext, preference: "auto", activeBeat: 4 }), "side");
assert.equal(resolveMapView({ ...interactionContext, preference: "auto", activeBeat: 5 }), "top");
assert.equal(resolveMapView({ ...interactionContext, preference: "side", activeBeat: 1 }), "side");
assert.equal(resolveMapView({ ...interactionContext, frameKind: "settlement", preference: "side", activeBeat: 3 }), "top");
assert.equal(resolveMapView({ ...interactionContext, branchView: "delta", preference: "side", activeBeat: 3 }), "top");
assert.match(mapViewLockReason({ ...interactionContext, frameKind: "comparison" }), /全国俯视/);

const heightScale = { domain: [20, 80], center: null, stops: [[20, "#000000"], [80, "#ffffff"]] };
assert.equal(normalizedHeight(20, heightScale), 0);
assert.equal(normalizedHeight(80, heightScale), 1);
assert.equal(normalizedHeight(100, heightScale), 1);
assert.ok(heightMetersForValue(80, heightScale) > heightMetersForValue(50, heightScale));
assert.equal(heightMetersForValue(null, heightScale), 0);

console.log(`presentation geometry verified: ${simulationFeatures.length} province anchors`);
