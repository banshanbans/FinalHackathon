export const SOUTH_CHINA_SEA_BOUNDARY_IMAGE_URL = "/assets/china-south-sea-standard-dashes.svg";
export const SOUTH_CHINA_SEA_BOUNDARY_GEOJSON_URL = "/assets/china-south-sea-standard-dashes.geojson";

/**
 * Cartographic placement for the official discontinuous-line crop.
 *
 * The source SVG stays byte-derived from GS(2016)1609. These four corners only
 * anchor that crop into the Presentation map coordinate system so MapLibre and
 * the SVG fallback apply the same pan, zoom, pitch and bearing as the national
 * map. The crop is render-only and is not used by simulation or spatial math.
 */
export const SOUTH_CHINA_SEA_BOUNDARY_CORNERS: [
  [number, number],
  [number, number],
  [number, number],
  [number, number],
] = [
  [106, 26],
  [127.5, 26],
  [127.5, 6],
  [106, 6],
];

export function SouthChinaSeaInset() {
  return <figure
    aria-label="中国南海诸岛附图，仅作全国版图展示，不参与本次推演计算"
    className="south-china-sea-inset"
    data-map-source="MNR-standard-map-GS2016-1609"
    data-positioning="map-viewport-fixed"
  >
    <img
      alt=""
      aria-hidden="true"
      src="/assets/china-south-sea-standard-overlay.svg"
    />
    <figcaption>南海诸岛</figcaption>
  </figure>;
}
