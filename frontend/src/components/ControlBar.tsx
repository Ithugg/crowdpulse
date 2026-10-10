import type { ConfigMsg, StateMsg } from '../types'

type Overlay = { boxes?: boolean; heatmap?: boolean; privacy?: boolean }

function Toggle({ label, hint, on, title, onClick }: { label: string; hint: string; on: boolean; title: string; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      title={title}
      onClick={onClick}
      className={`flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-brand ${
        on ? 'border-brand/50 bg-brand/10 text-ink' : 'border-line text-muted hover:border-line-strong hover:text-ink'
      }`}
    >
      {label}
      <kbd>{hint}</kbd>
    </button>
  )
}

/** What is drawn on the video. Lives in the top bar so the camera row has room for every source. */
export function OverlayToggles({ state, onOverlay, onRestart }: { state: StateMsg | null; onOverlay: (overlay: Overlay) => void; onRestart: () => void }) {
  const overlay = state?.overlay ?? { boxes: true, heatmap: true, privacy: true }
  return (
    <div className="flex items-center gap-1.5">
      <Toggle label="Boxes" hint="B" on={overlay.boxes} title="Outline each detected person" onClick={() => onOverlay({ boxes: !overlay.boxes })} />
      <Toggle label="Heatmap" hint="H" on={overlay.heatmap} title="Colour people by the local density around them" onClick={() => onOverlay({ heatmap: !overlay.heatmap })} />
      <Toggle label="Privacy" hint="V" on={overlay.privacy} title="Pixelate every detected head: people are counted, never identified" onClick={() => onOverlay({ privacy: !overlay.privacy })} />
      <Toggle label="Restart" hint="R" on={false} title="Restart this camera and clear its history" onClick={onRestart} />
    </div>
  )
}

/** Demo mode: switch camera instantly with the number keys. */
export function ControlBar({ config, onSource }: { config: ConfigMsg | null; onSource: (id: string) => void }) {
  return (
    <div className="scroll-thin flex shrink-0 items-center gap-1 overflow-x-auto rounded-lg border border-line bg-panel p-1" role="group" aria-label="Camera source">
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
            className={`flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors focus-visible:outline-2 focus-visible:outline-brand disabled:cursor-not-allowed disabled:opacity-35 ${
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
  )
}
