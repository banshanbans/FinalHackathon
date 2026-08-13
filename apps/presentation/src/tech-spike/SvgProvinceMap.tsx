import { useEffect, useState } from "react";

import { frameDelta } from "./presentationData";

function deltaColor(value: number) {
  if (value <= -5) return "#6656c8";
  if (value <= -1.5) return "#34416d";
  if (value < 1.5) return "#172638";
  if (value < 5) return "#176c72";
  return "#22b9ad";
}

export function SvgProvinceMap({
  frame,
  selectedCode,
  onSelect,
}: {
  frame: number;
  selectedCode: string | null;
  onSelect: (code: string, name: string) => void;
}) {
  const [svg, setSvg] = useState("");

  useEffect(() => {
    let active = true;
    void fetch("/assets/china-analysis-map.svg")
      .then((response) => {
        if (!response.ok) throw new Error(`SVG_${response.status}`);
        return response.text();
      })
      .then((value) => active && setSvg(value));
    return () => {
      active = false;
    };
  }, []);

  const colorRules = Array.from({ length: 100 }, (_, numericCode) => {
    const code = String(numericCode).padStart(2, "0");
    const selected = code === selectedCode;
    return `.svg-renderer path[data-region-role="simulation-province"][data-code="${code}"]{fill:${deltaColor(frameDelta(code, frame))};stroke:${selected ? "#f4d49b" : "rgba(177,212,240,.72)"};stroke-width:${selected ? "1.8" : ".65"}}`;
  }).join("");

  return (
    <div className="map-renderer svg-renderer-shell">
      <style>{`.svg-renderer path[data-region-role="territory-context"]{fill:#12343e;stroke:rgba(117,234,214,.76);stroke-width:1.1;pointer-events:none}${colorRules}`}</style>
      <div
        aria-label="中国全国版图 SVG 兼容地图（31 省参与推演）"
        className="svg-renderer"
        dangerouslySetInnerHTML={{ __html: svg }}
        onClick={(event) => {
          const path = (event.target as Element).closest<SVGPathElement>(
            'path[data-region-role="simulation-province"][data-code]',
          );
          if (!path) return;
          const code = path.dataset.code ?? "";
          onSelect(code, path.getAttribute("name") ?? code);
        }}
      />
    </div>
  );
}
