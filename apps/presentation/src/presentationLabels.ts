import type { SimulationRound } from "./contracts";

export const ROUND_LABELS: Record<SimulationRound, string> = {
  province_initial: "省级初始行动",
  automaker_initial: "车企初步响应",
  province_revision: "省级策略调整",
  automaker_negotiation: "政企谈判",
  province_counter_response: "省级回应",
  automaker_final: "车企最终行动",
  environment_settlement: "环境结算",
};

export const FILL_METRIC_LABELS: Record<string, string> = {
  central_share: "中央承担比例",
  local_subsidy_intensity: "地方新能源汽车补贴支持强度",
  automaker_sales_activity: "车企销售投入强度",
  accepted_counteroffers: "反报价接受数量",
  province_nev_development_index: "新能源汽车发展指数",
  development_delta: "发展指数差值",
  event_exposure: "事件暴露强度",
};

export const EVENT_FAMILY_LABELS: Record<string, string> = {
  technology: "技术情景",
  regulation: "监管情景",
  energy: "能源情景",
  supply_chain: "供应链情景",
  scenario: "机制情景",
};

export const OVERLAY_STATUS_LABELS: Record<string, string> = {
  competition_loss: "竞争挤出",
  offered: "已报价",
  accept: "已接受",
  accepted: "已接受",
  reject: "已拒绝",
  rejected: "已拒绝",
  matched: "已生效",
  unmatched: "未匹配",
  invalid: "资源无效",
  reallocated: "已重配",
  low: "低强度",
  medium: "中强度",
  high: "高强度",
};

export const MECHANISM_CHANNEL_LABELS: Record<string, string> = {
  battery_access: "电池供应可达性",
  logistics_cost: "物流成本",
  industry_activity: "产业活动",
  intelligent_driving_readiness: "智驾能力基础",
  consumer_acceptance: "消费接受度",
  rd_activity: "研发活动",
  consumer_trust: "消费信任",
  enterprise_liability_cost: "车企责任成本",
  regulatory_pilot: "监管试点",
  relative_use_cost: "相对使用成本",
  wtp_demand: "消费意愿与需求",
};

function labelFor(table: Record<string, string>, value: string, fallback: string) {
  const label = table[value];
  if (!label && import.meta.env.DEV) {
    console.warn(`[presentation-labels] unknown value: ${value}`);
  }
  return label ?? fallback;
}

export function fillMetricLabel(value: string) {
  return labelFor(FILL_METRIC_LABELS, value, "未知指标");
}

export function eventFamilyLabel(value: string) {
  return labelFor(EVENT_FAMILY_LABELS, value, "机制情景");
}

export function overlayStatusLabel(value: string) {
  return labelFor(OVERLAY_STATUS_LABELS, value, "未知状态");
}

export function mechanismChannelLabel(value: string) {
  return labelFor(MECHANISM_CHANNEL_LABELS, value, "未知机制");
}
