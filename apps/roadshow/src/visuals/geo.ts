import type { RoadshowFeatureCollection, RoadshowMapFeature } from "../contracts";
import { geoArea } from "d3-geo";

type PolygonCoordinates = RoadshowMapFeature["geometry"]["coordinates"][number];

function polygonArea(coordinates: PolygonCoordinates): number {
  return geoArea({
    type: "Feature",
    properties: {},
    geometry: { type: "MultiPolygon", coordinates: [coordinates] },
  });
}

export function featureForD3(feature: RoadshowMapFeature): RoadshowMapFeature {
  return {
    ...feature,
    geometry: {
      ...feature.geometry,
      coordinates: feature.geometry.coordinates.map((polygon) => {
        const reversed = polygon.map((ring) => [...ring].reverse());
        return polygonArea(reversed) < polygonArea(polygon) ? reversed : polygon;
      }),
    },
  };
}

export function collectionForD3(collection: RoadshowFeatureCollection): RoadshowFeatureCollection {
  return {
    ...collection,
    features: collection.features.map(featureForD3),
  };
}
