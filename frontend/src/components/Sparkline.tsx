interface Props {
  values: number[]
  warn: number
  critical: number
  color: string
}

const W = 240
const H = 44

/** Last minute of density for one zone, with the two thresholds drawn as dashed guides. */
export function Sparkline({ values, warn, critical, color }: Props) {
  const top = Math.max(critical * 1.2, ...values) || 1
  const y = (v: number) => H - 2 - (v / top) * (H - 4)
  const x = (i: number) => (values.length <= 1 ? W : (i / (values.length - 1)) * W)
  const line = values.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')

  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="h-11 w-full" aria-hidden>
      <line x1="0" x2={W} y1={y(critical)} y2={y(critical)} stroke="#ff4f61" strokeOpacity="0.55" strokeDasharray="3 4" vectorEffect="non-scaling-stroke" />
      <line x1="0" x2={W} y1={y(warn)} y2={y(warn)} stroke="#f6b93b" strokeOpacity="0.4" strokeDasharray="3 4" vectorEffect="non-scaling-stroke" />
      {values.length > 1 && (
        <>
          <path d={`${line} L${W},${H} L0,${H} Z`} fill={color} fillOpacity="0.12" />
          <path d={line} fill="none" stroke={color} strokeWidth="1.75" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        </>
      )}
    </svg>
  )
}
