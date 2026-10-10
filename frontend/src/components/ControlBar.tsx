import type { ConfigMsg, StateMsg } from '../types'

interface Props {
  config: ConfigMsg | null
  state: StateMsg | null
  onSource: (id: string) => void
  onOverlay: (overlay: { boxes?: boolean; heatmap?: boolean; privacy?: boolean }) => void
  onRestart: () => void
}

function Toggle({ label, hint, on, onClick }: { label: string; hint: string; on: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-brand ${
        on ? 'border-brand/50 bg-brand/10 text-ink' : 'border-line text-muted hover:border-line-strong hover:text-ink'
      }`}
    >
      {label}
      <kbd>{hint}</kbd>
    </button>
  )
}

/** Demo mode: switch camera instantly (keys 1-9), toggle overlays, restart the clip. */
export function ControlBar({ config, state, onSource, onOverlay, onRestart }: Props) {
  const overlay = state?.overlay ?? { boxes: true, heatmap: true, privacy: true }

  return (
    <div className="flex shrink-0 flex-wrap items-center gap-2">
      <div className="flex items-center gap-1 rounded-lg border border-line bg-panel p-1" role="group" aria-label="Camera source">
        {config?.sources.map((source, i) => {
          const active = source.id === config.active_source
          return (
            <button
              key={source.id}
              type="button"
              disabled={!source.available}
              aria-pressed={active}
              onClick={() => onSource(source.id)}
              title={source.available ? undefined : 'Video file not found in media/'}
              className={`flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-brand disabled:cursor-not-allowed disabled:opacity-35 ${
                active ? 'bg-raised text-ink shadow-[inset_0_0_0_1px_var(--color-line-strong)]' : 'text-muted hover:text-ink'
              }`}
            >
              {source.kind === 'webcam' && <span className={`h-1.5 w-1.5 rounded-full ${active ? 'bg-crit' : 'bg-dim'}`} />}
              {source.label}
              <kbd>{i + 1}</kbd>
            </button>
          )
        })}
      </div>

      <div className="ml-auto flex items-center gap-1.5">
        <Toggle label="Boxes" hint="B" on={overlay.boxes} onClick={() => onOverlay({ boxes: !overlay.boxes })} />
        <Toggle label="Heatmap" hint="H" on={overlay.heatmap} onClick={() => onOverlay({ heatmap: !overlay.heatmap })} />
        <Toggle label="Privacy" hint="V" on={overlay.privacy} onClick={() => onOverlay({ privacy: !overlay.privacy })} />
        <Toggle label="Restart" hint="R" on={false} onClick={onRestart} />
      </div>
    </div>
  )
}
