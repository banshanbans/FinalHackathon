export type MapViewPreference = "auto" | "top" | "side";
export type MapViewMode = "top" | "side";

interface MapViewContext {
  preference: MapViewPreference;
  activeBeat: number;
  frameKind: string;
  branchView: "control" | "treatment" | "delta";
  hasSpotlight: boolean;
}

export function mapViewLockReason(context: Omit<MapViewContext, "preference" | "activeBeat">): string | null {
  if (context.branchView === "delta") return "方案差值固定使用全国俯视";
  if (context.frameKind === "settlement" || context.frameKind === "comparison") {
    return "结算与年度比较固定使用全国俯视";
  }
  if (!context.hasSpotlight) return "当前帧没有可进入侧视的互动主体";
  return null;
}

export function resolveMapView(context: MapViewContext): MapViewMode {
  if (mapViewLockReason(context)) return "top";
  if (context.preference === "auto") {
    return context.activeBeat === 3 || context.activeBeat === 4 ? "side" : "top";
  }
  return context.preference;
}
