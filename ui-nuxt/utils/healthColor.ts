/**
 * Returns a CSS color string based on a health score.
 * Green: >= 80, Amber: 50-79, Red: < 50, Grey: no score (undefined)
 */
export function healthColor(score: number | undefined): string {
  if (score === undefined) return '#475569'
  if (score >= 80) return '#2ed573'
  if (score >= 50) return '#ffa502'
  return '#ff4757'
}
