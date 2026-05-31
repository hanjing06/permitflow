// Color palette per D-32 / D-33. Status → hex.
//   amber  = merged cluster (coordinated, win)
//   shifted-red = conflict_deferred (visible cost of doing nothing)
//   neutral = singleton OR naive (no opinion)
//   muted  = unknown / default
export const STATUS_COLOR = {
  coordinated:        "#f59e0b", // amber — confirmed trench-share
  review_cluster:     "#3b82f6", // blue  — same-street, review-only (anchor_program)
  conflict_deferred:  "#dc2626", // shifted red
  singleton:          "#9ca3af", // neutral gray
  naive:              "#6b7280", // slate (independent)
};

export const STATUS_FILL_OPACITY = {
  coordinated:        0.55,
  conflict_deferred:  0.55,
  singleton:          0.35,
  naive:              0.40,
};

export function colorFor(status) {
  return STATUS_COLOR[status] || "#6b7280";
}

export function fillOpacityFor(status) {
  return STATUS_FILL_OPACITY[status] ?? 0.40;
}
