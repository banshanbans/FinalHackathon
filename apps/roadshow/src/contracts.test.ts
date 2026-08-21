import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import {
  RoadshowContentSchema,
  RoadshowFeatureCollectionSchema,
  validateRoadshowMap,
} from "./contracts";

function readJson(relativePath: string): unknown {
  return JSON.parse(readFileSync(new URL(relativePath, import.meta.url), "utf8")) as unknown;
}

describe("roadshow static contracts", () => {
  it("validates the four-scene 13110 roadshow content", () => {
    const content = RoadshowContentSchema.parse(readJson("../public/data/roadshow-content.json"));
    expect(content.hero.brand).toBe("13110");
    expect(content.hero.slogan).toBe("让政策影响，被看见。");
    expect(content.explainer.presets).toEqual([
      { region: "西部", central_share: 95, local_share: 5 },
      { region: "中部", central_share: 90, local_share: 10 },
      { region: "东部", central_share: 85, local_share: 15 },
    ]);
    expect(content.explainer.impacts).toEqual(["财政空间", "地方政策", "企业行动", "产业布局"]);
    expect(content.identity.items.map((item) => item.value)).toEqual([1, 31, 10]);
    expect(content.chapters.map((chapter) => chapter.index)).toEqual([1, 2, 3, 4]);
  });

  it("requires 31 simulated provinces and three territory context features", () => {
    const map = validateRoadshowMap(
      RoadshowFeatureCollectionSchema.parse(readJson("../public/data/china-presentation-map.geojson")),
    );
    const simulated = map.features.filter(
      (feature) => feature.properties.region_role === "simulation-province",
    );
    const context = map.features.filter(
      (feature) => feature.properties.region_role === "territory-context",
    );
    expect(simulated).toHaveLength(31);
    expect(context).toHaveLength(3);
    expect(new Set(map.features.map((feature) => feature.properties.province_code)).size).toBe(34);
    expect(context.map((feature) => feature.properties.name).sort()).toEqual(["台湾", "澳门", "香港"]);
    expect(context.every((feature) => !feature.properties.interactive)).toBe(true);
    expect(context.every((feature) => !feature.properties.included_in_simulation)).toBe(true);
  });
});
