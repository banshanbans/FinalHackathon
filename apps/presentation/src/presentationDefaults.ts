export const REFERENCE_POLICY_SHARES = {
  west: 95,
  central: 90,
  east: 85,
} as const;

// This preset is intentionally aligned with the fully warmed production Luna cache.
// It changes only the initial Treatment selection; the 2025 reference policy stays fixed.
export const CACHED_TREATMENT_SHARES = {
  west: 96,
  central: 93,
  east: 82,
} as const;
