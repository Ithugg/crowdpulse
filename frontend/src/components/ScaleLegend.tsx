import { LEVEL } from '../format'
import type { Calibration, LevelInfo } from '../types'

function describe(calibration: Calibration): { text: string; title: string } {
  if (calibration.mode === 'ground') {
    return {
      text: `Auto-calibrated: camera ${calibration.cam_height_m} m high, ${calibration.tilt_deg}° down`,
      title:
        'Real distances are measured, not typed in. The people in view act as a ruler (average height 1.7 m), ' +
        `which gives the camera height and tilt and so the floor position of every person. Lens assumed ${calibration.hfov_deg}° wide.`,
    }
  }
  return {
    text: 'Distance from body size',
    title:
      'Feet are not visible often enough to calibrate against the floor, so each person’s distance is taken ' +
      `from their apparent width (shoulders about 0.5 m). Lens assumed ${calibration.hfov_deg}° wide.`,
  }
}

/** The research density scale behind the zone colours, plus how this camera is being measured. */
export function ScaleLegend({ levels, calibration }: { levels: LevelInfo[]; calibration: Calibration }) {
  const measured = describe(calibration)

  return (
    <div className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted">
      <span className="font-semibold uppercase tracking-wider text-dim">Density scale, people/m²</span>
      {levels.map((level, i) => {
        const next = levels[i + 1]
        const range = next ? (level.min === 0 ? `< ${next.min}` : `${level.min}–${next.min}`) : `≥ ${level.min}`
        return (
          <span key={level.id} className="flex cursor-help items-center gap-1" title={`${level.what}\nSource: ${level.source}`}>
            <span className={`h-2 w-2 rounded-sm ${LEVEL[level.id].dot}`} style={{ opacity: level.id === 'normal' ? 0.45 : 1 }} />
            <span className="num">{range}</span>
            <span className={level.id === 'normal' || level.id === 'busy' ? '' : LEVEL[level.id].text}>{level.label}</span>
          </span>
        )
      })}
      <span className="hidden text-dim xl:inline">Fruin · Still · UK Green Guide · Helbing et al. 2007</span>
      <span className="ml-auto flex cursor-help items-center gap-1.5 text-brand" title={measured.title}>
        <svg viewBox="0 0 16 16" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
          <circle cx="8" cy="8" r="5.5" />
          <path d="M8 1v3M8 12v3M1 8h3M12 8h3" strokeLinecap="round" />
        </svg>
        {measured.text}
      </span>
    </div>
  )
}
