import { forwardRef, useState } from 'react'
import type { StateMsg } from '../types'

export type Toggle = 'boxes' | 'heatmap' | 'grid' | 'privacy'

interface Props {
  state: StateMsg | null
  gridAvailable: boolean
  onToggle: (which: Toggle) => void
  onReset: () => void
  /** Runs a typed command; returns an error message, or null when it was understood. */
  onCommand: (text: string) => string | null
}

/** The keys that drive the console, and a command line for the same actions by name. */
export const KeyBar = forwardRef<HTMLInputElement, Props>(function KeyBar({ state, gridAvailable, onToggle, onReset, onCommand }, ref) {
  const [text, setText] = useState('')
  const [problem, setProblem] = useState<string | null>(null)
  const overlay = state?.overlay ?? { boxes: true, heatmap: true, privacy: true, grid: false }

  return (
    <footer className="keybar">
      <button type="button" className="key" aria-pressed={overlay.boxes} onClick={() => onToggle('boxes')} title="Mark each detected person">
        <kbd>B</kbd>Marks
      </button>
      <button type="button" className="key" aria-pressed={overlay.heatmap} onClick={() => onToggle('heatmap')} title="Tint the video where local density is 2 people/m² or more">
        <kbd>H</kbd>Heat
      </button>
      <button
        type="button"
        className="key"
        aria-pressed={overlay.grid && gridAvailable}
        disabled={!gridAvailable}
        onClick={() => onToggle('grid')}
        title={gridAvailable ? 'Draw the calibrated floor as a grid of 2 m squares' : 'No floor grid: this camera is not calibrated against the floor'}
      >
        <kbd>G</kbd>Grid 2 m
      </button>
      <button type="button" className="key" aria-pressed={overlay.privacy} onClick={() => onToggle('privacy')} title="Blur every detected head: people are counted, never identified">
        <kbd>V</kbd>Privacy
      </button>
      <button type="button" className="key" onClick={onReset} title="Restart this camera and clear its history">
        <kbd>R</kbd>Reset
      </button>

      <form
        className="command"
        data-bad={problem !== null}
        onSubmit={(e) => {
          e.preventDefault()
          const result = onCommand(text)
          setProblem(result)
          if (result === null) setText('')
        }}
      >
        <label htmlFor="command">/</label>
        <input
          id="command"
          ref={ref}
          value={text}
          autoComplete="off"
          spellCheck={false}
          placeholder="command: C4, Z2 PLAN, REPORT, ACK, GRID"
          onChange={(e) => {
            setText(e.target.value)
            setProblem(null)
          }}
          onKeyDown={(e) => {
            if (e.key === 'Escape') e.currentTarget.blur()
          }}
        />
        {problem && <span role="alert">{problem}</span>}
      </form>
    </footer>
  )
})
