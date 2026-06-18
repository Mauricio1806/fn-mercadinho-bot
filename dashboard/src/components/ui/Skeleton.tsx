/**
 * Skeleton — placeholder de loading reutilizável.
 * Usa a animação .loading-pulse já definida no index.css.
 */

import type { CSSProperties } from "react";

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  radius?: string | number;
  style?: CSSProperties;
}

export function Skeleton({
  width = "100%",
  height = 16,
  radius = 6,
  style,
}: SkeletonProps) {
  return (
    <div
      className="loading-pulse"
      style={{ width, height, borderRadius: radius, ...style }}
    />
  );
}
