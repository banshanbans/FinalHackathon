import { z } from "zod";

export const RoadshowContentSchema = z
  .object({
    schema_version: z.literal("roadshow-content-v3"),
    hero: z
      .object({
        brand: z.literal("13110"),
        descriptor: z.string().min(1),
        slogan: z.string().min(1),
        cta: z.string().min(1),
      })
      .strict(),
    explainer: z
      .object({
        consumer: z
          .object({
            eyebrow: z.string().min(1),
            product: z.string().min(1),
            subsidy_label: z.string().min(1),
            subsidy_rate: z.literal("20%"),
            price_label: z.string().min(1),
          })
          .strict(),
        funding: z
          .object({
            question: z.string().min(1),
            central_label: z.string().min(1),
            local_label: z.string().min(1),
            pool_label: z.string().min(1),
            unit_label: z.literal("份"),
          })
          .strict(),
        presets: z
          .array(
            z
              .object({
                region: z.enum(["西部", "中部", "东部"]),
                central_share: z.union([z.literal(95), z.literal(90), z.literal(85)]),
                local_share: z.union([z.literal(5), z.literal(10), z.literal(15)]),
              })
              .strict(),
          )
          .length(3),
        ignition_question: z.string().min(1),
        impacts: z.array(z.string().min(1)).length(4),
      })
      .strict(),
    identity: z
      .object({
        items: z
          .array(
            z
              .object({
                value: z.union([z.literal(1), z.literal(31), z.literal(10)]),
                label: z.string().min(1),
              })
              .strict(),
          )
          .length(3),
        handoff_label: z.string().min(1),
        decision_question: z.string().min(1),
      })
      .strict(),
    chapters: z
      .array(
        z
          .object({
            id: z.enum([
              "scene-00-orbital",
              "scene-01-china-focus",
              "scene-02-identity-reveal",
              "scene-03-causal-handoff",
            ]),
            index: z.number().int().min(1).max(4),
            label: z.string().min(1),
            title: z.string().min(1),
          })
          .strict(),
      )
      .length(4),
  })
  .strict();

const PositionSchema = z.array(z.number().finite()).min(2);
const LinearRingSchema = z.array(PositionSchema).min(4);
const PolygonCoordinatesSchema = z.array(LinearRingSchema).min(1);
const MultiPolygonCoordinatesSchema = z.array(PolygonCoordinatesSchema).min(1);

export const RoadshowMapFeatureSchema = z
  .object({
    type: z.literal("Feature"),
    properties: z
      .object({
        province_code: z.string().min(1),
        name: z.string().min(1),
        region_role: z.enum(["simulation-province", "territory-context"]),
        included_in_simulation: z.boolean(),
        interactive: z.boolean(),
        representation: z.string().min(1),
      })
      .passthrough(),
    geometry: z
      .object({
        type: z.literal("MultiPolygon"),
        coordinates: MultiPolygonCoordinatesSchema,
      })
      .strict(),
  })
  .passthrough();

export const RoadshowFeatureCollectionSchema = z
  .object({
    type: z.literal("FeatureCollection"),
    features: z.array(RoadshowMapFeatureSchema).length(34),
  })
  .passthrough();

export type RoadshowContentV3 = z.infer<typeof RoadshowContentSchema>;
export type RoadshowMapFeature = z.infer<typeof RoadshowMapFeatureSchema>;
export type RoadshowFeatureCollection = z.infer<typeof RoadshowFeatureCollectionSchema>;

export function validateRoadshowMap(collection: RoadshowFeatureCollection): RoadshowFeatureCollection {
  const provinceCodes = new Set(collection.features.map((feature) => feature.properties.province_code));
  const simulated = collection.features.filter(
    (feature) => feature.properties.region_role === "simulation-province",
  );
  const context = collection.features.filter(
    (feature) => feature.properties.region_role === "territory-context",
  );
  const contextNames = new Set(context.map((feature) => feature.properties.name));

  if (provinceCodes.size !== 34) throw new Error("地图省级代码不唯一");
  if (simulated.length !== 31 || context.length !== 3) {
    throw new Error("地图必须包含31个模拟省份和3个地域背景");
  }
  if (!["香港", "澳门", "台湾"].every((name) => contextNames.has(name))) {
    throw new Error("地域背景必须包含香港、澳门和台湾");
  }
  if (context.some((feature) => feature.properties.included_in_simulation || feature.properties.interactive)) {
    throw new Error("港澳台地域背景不得参与模拟或交互");
  }
  if (simulated.some((feature) => !feature.properties.included_in_simulation)) {
    throw new Error("31个模拟省份必须全部纳入推演范围");
  }
  return collection;
}
