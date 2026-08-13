import type { ProvinceProfile, ProvinceState } from "../types";

const COORDINATES: Record<string, [number, number]> = {
  "11": [70, 32], "12": [75, 35], "13": [68, 38], "14": [59, 39],
  "15": [56, 24], "21": [80, 27], "22": [86, 19], "23": [89, 9],
  "31": [78, 55], "32": [73, 52], "33": [75, 62], "34": [67, 57],
  "35": [69, 71], "36": [61, 66], "37": [69, 45], "41": [60, 50],
  "42": [55, 59], "43": [53, 68], "44": [57, 81], "45": [46, 81],
  "46": [50, 93], "50": [43, 62], "51": [34, 59], "52": [42, 71],
  "53": [31, 80], "54": [14, 58], "61": [49, 49], "62": [35, 40],
  "63": [25, 48], "64": [44, 39], "65": [13, 28],
};

const OUTLINE = "M5 21 L16 9 L31 11 L43 4 L58 10 L70 5 L88 8 L96 21 L89 35 L93 48 L83 58 L80 72 L68 76 L61 88 L51 86 L43 96 L31 87 L21 79 L9 67 L13 52 L4 41 Z";

function valueColor(value: number) {
  if (value >= 64) return "#26d7b0";
  if (value >= 56) return "#28b8df";
  if (value >= 48) return "#6485e8";
  return "#7a6f9e";
}

interface ProvinceMapProps {
  profiles: ProvinceProfile[];
  states: Record<string, ProvinceState>;
  selectedCode: string;
  onSelect: (code: string) => void;
}

export function ProvinceMap({ profiles, states, selectedCode, onSelect }: ProvinceMapProps) {
  return (
    <div className="map-wrap" aria-label="中国省域态势示意图">
      <svg className="province-map" role="img" viewBox="0 0 100 100">
        <title>31 省政策收益指数态势图</title>
        <defs>
          <linearGradient id="map-surface" x1="0" x2="1" y1="0" y2="1">
            <stop offset="0" stopColor="#0d2940" />
            <stop offset="1" stopColor="#081923" />
          </linearGradient>
          <filter id="node-glow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="1.2" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <path d={OUTLINE} fill="url(#map-surface)" stroke="#28536a" strokeDasharray="1.2 1.2" strokeWidth=".5" />
        {profiles.map((profile) => {
          const coordinate = COORDINATES[profile.province_code];
          if (!coordinate) return null;
          const value = states[profile.province_code]?.policy_benefit_index ?? 50;
          const selected = selectedCode === profile.province_code;
          return (
            <g
              className="map-province"
              data-testid={`province-${profile.province_code}`}
              key={profile.province_code}
              onClick={() => onSelect(profile.province_code)}
              onKeyDown={(event) => event.key === "Enter" && onSelect(profile.province_code)}
              role="button"
              tabIndex={0}
              transform={`translate(${coordinate[0]} ${coordinate[1]})`}
            >
              {selected && <circle fill="none" r="4" stroke="#ffb55b" strokeWidth=".7" />}
              <circle
                fill={valueColor(value)}
                filter={selected ? "url(#node-glow)" : undefined}
                r={selected ? 2.3 : 1.8}
                stroke="#d8fbff"
                strokeWidth=".25"
              />
              <text className="map-label" textAnchor="middle" y="-2.8">{profile.short_name}</text>
            </g>
          );
        })}
      </svg>
      <div className="map-legend">
        <span>政策收益指数</span>
        <i className="legend-gradient" />
        <small>低</small><small>高</small>
      </div>
      <span className="map-note">示意布局 · 非行政边界底图</span>
    </div>
  );
}
