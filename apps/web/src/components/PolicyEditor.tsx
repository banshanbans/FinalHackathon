import type { Policy } from "../types";

const fields = [
  ["west_central_share", "西部 12 省", "参考 95%"],
  ["central_central_share", "中部 10 省", "参考 90%"],
  ["east_central_share", "东部 9 省", "参考 85%"],
] as const;

export function PolicyEditor({ policy, onChange, readOnly = false }: { policy: Policy; onChange: (policy: Policy) => void; readOnly?: boolean }) {
  const hasOrderingWarning = !(policy.west_central_share >= policy.central_central_share && policy.central_central_share >= policy.east_central_share);
  return <div className="v3-policy-editor">
    {fields.map(([field, label, hint]) => <label key={field}><span><strong>{label}</strong><small>{hint}</small></span><input aria-label={`${label}中央承担比例`} disabled={readOnly} max="100" min="0" onChange={(event) => onChange({ ...policy, input_mode: "absolute", share_adjustments: { west: 0, central: 0, east: 0 }, [field]: Number(event.target.value) / 100 })} step="1" type="number" value={(policy[field] * 100).toFixed(0)} /><b>%</b></label>)}
    {hasOrderingWarning && <div className="v3-policy-warning" role="alert">当前比例偏离西部≥中部≥东部的参考排序；允许继续用于机制实验。</div>}
  </div>;
}
