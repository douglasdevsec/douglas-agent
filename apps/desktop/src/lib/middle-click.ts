import type * as React from 'react'

/** `MouseEvent.button` for the middle (wheel) button. */
const MIDDLE_BUTTON = 1

/** The element a middle press started on. One pointer can hold one button, so
 *  a single module-level slot is the whole state — and it is only ever read by
 *  identity in the pointerup immediately after, so a leftover value (released
 *  off-element) is inert rather than stale. */
let pressedOn: EventTarget | null = null

export interface MiddleClickHandlers {
  onMouseDown: (event: React.MouseEvent) => void
  onPointerDown: (event: React.PointerEvent) => void
  onPointerUp: (event: React.PointerEvent) => void
}

/**
 * Middle-click as a gesture that survives a real three-button mouse.
 *
 * `auxclick` is the obvious event and the wrong one to build on. Windows and
 * Linux Chromium answer a middle press inside a scroller by starting the
 * AUTOSCROLL pan, and the mouseup that ends the pan is spent stopping it
 * instead of completing a click — so `auxclick` never arrives. Every surface
 * carrying this gesture (tab strips, the session list, the terminal rail) is a
 * scroller, which is why middle-click only ever worked on macOS, where
 * autoscroll doesn't exist.
 *
 * Pointer events fire either way, so the gesture is armed on pointerdown and
 * spent on the pointerup over the SAME element — press one tab, release on
 * another and nothing closes (Chrome / VS Code semantics). mousedown's default
 * is killed on every middle press, action or not, so the pan widget can never
 * appear on a surface that owns the button.
 *
 * A plain factory, not a hook: tab strips call it inside `map()`.
 */
export function middleClickHandlers(action: (() => void) | undefined): MiddleClickHandlers {
  return {
    onMouseDown: event => {
      if (event.button === MIDDLE_BUTTON) {
        event.preventDefault()
      }
    },

    onPointerDown: event => {
      if (event.button === MIDDLE_BUTTON) {
        pressedOn = action ? event.currentTarget : null
      }
    },

    onPointerUp: event => {
      if (event.button !== MIDDLE_BUTTON) {
        return
      }

      const armed = pressedOn === event.currentTarget
      pressedOn = null

      if (armed) {
        event.preventDefault()
        action?.()
      }
    }
  }
}
