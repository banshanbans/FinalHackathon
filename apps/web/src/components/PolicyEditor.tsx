import type { Policy } from "../types";

function percent(value: number) {
  return Math.round(value * 100);
}

function RangeField({
  label,
  value,
  min = 0,
  max = 100,
  step = 1,
  suffix = "",
  onChange,
  disabled = false,
}: {
  label: string;
  value: number;
  min?: number;
  max?: number;
  step?: number;
  suffix?: string;
  onChange: (value: number) => void;
  disabled?: boolean;
}) {
  return (
    <label className="range-field">
      <span>{label}<strong>{value.toFixed(step < 1 ? 2 : 0)}{suffix}</strong></span>
      <input
        disabled={disabled}
        max={max}
        min={min}
        onChange={(event) => onChange(Number(event.target.value))}
        step={step}
        type="range"
        value={value}
      />
    </label>
  );
}

function MixEditor({
  label,
  values,
  labels,
  onChange,
  disabled = false,
}: {
  label: string;
  values: Record<string, number>;
  labels: Record<string, string>;
  onChange: (key: string, value: number) => void;
  disabled?: boolean;
}) {
  const sum = Object.values(values).reduce((total, value) => total + value, 0);
  return (
    <div className="mix-editor">
      <div className="mix-header">
        <span>{label}</span>
        <strong className={Math.abs(sum - 1) < 0.000001 ? "valid" : "invalid"}>
          合计 {percent(sum)}%
        </strong>
      </div>
      <div className="mix-fields">
        {Object.entries(values).map(([key, value]) => (
          <label key={key}>
            <span>{labels[key]}</span>
            <input
              aria-label={`${label}-${labels[key]}`}
              disabled={disabled}
              max={100}
              min={0}
              onChange={(event) => onChange(key, Number(event.target.value) / 100)}
              step={1}
              type="number"
              value={percent(value)}
            />
            <em>%</em>
          </label>
        ))}
      </div>
    </div>
  );
}

export function PolicyEditor({
  policy,
  onChange,
  compact = false,
  readOnly = false,
}: {
  policy: Policy;
  onChange: (policy: Policy) => void;
  compact?: boolean;
  readOnly?: boolean;
}) {
  return (
    <div className={`policy-editor ${compact ? "compact" : ""} ${readOnly ? "read-only" : ""}`}>
      <div className="range-grid">
        <RangeField
          disabled={readOnly}
          label="支持强度"
          onChange={(support_intensity) => onChange({ ...policy, support_intensity })}
          value={policy.support_intensity}
        />
        <RangeField
          disabled={readOnly}
          label="地方配套要求"
          onChange={(value) => onChange({ ...policy, local_match_requirement: value / 100 })}
          suffix="%"
          value={percent(policy.local_match_requirement)}
        />
        <RangeField
          disabled={readOnly}
          label="中小企业倾斜"
          onChange={(value) => onChange({ ...policy, sme_preference: value / 100 })}
          suffix="%"
          value={percent(policy.sme_preference)}
        />
        <RangeField
          disabled={readOnly}
          label="区域支持倾斜"
          max={1}
          min={-1}
          onChange={(regional_support_bias) => onChange({ ...policy, regional_support_bias })}
          step={0.05}
          value={policy.regional_support_bias}
        />
      </div>
      <MixEditor
        disabled={readOnly}
        label="政策工具组合"
        labels={{
          direct_subsidy: "直接补贴",
          interest_subsidy: "贷款贴息",
          financing_guarantee: "融资担保",
        }}
        onChange={(key, value) => onChange({
          ...policy,
          instrument_mix: { ...policy.instrument_mix, [key]: value },
        })}
        values={{ ...policy.instrument_mix }}
      />
      <MixEditor
        disabled={readOnly}
        label="设备更新技术组合"
        labels={{ digital: "数字化", green: "绿色", general: "基础技改" }}
        onChange={(key, value) => onChange({
          ...policy,
          technology_mix: { ...policy.technology_mix, [key]: value },
        })}
        values={{ ...policy.technology_mix }}
      />
    </div>
  );
}
