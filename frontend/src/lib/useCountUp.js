import { useEffect, useRef, useState } from "react";

// Linear-ish ease-out tween from previous value to `target` over `durationMs`.
// On first render, starts at 0. On subsequent target changes, tweens from the
// last displayed value to the new target. ~60fps via requestAnimationFrame.
export function useCountUp(target, durationMs = 2000) {
  const [value, setValue] = useState(0);
  const fromRef = useRef(0);
  const startRef = useRef(null);
  const rafRef = useRef(null);

  useEffect(() => {
    if (target == null || Number.isNaN(target)) return;
    fromRef.current = value;
    startRef.current = null;
    cancelAnimationFrame(rafRef.current);

    const tick = (ts) => {
      if (startRef.current == null) startRef.current = ts;
      const elapsed = ts - startRef.current;
      const t = Math.min(1, elapsed / durationMs);
      const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic
      const next = fromRef.current + (target - fromRef.current) * eased;
      setValue(next);
      if (t < 1) rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, durationMs]);

  return value;
}
