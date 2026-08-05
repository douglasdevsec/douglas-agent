import { cleanup, render } from '@testing-library/react'
import { afterEach, beforeAll, describe, expect, it } from 'vitest'

import { Checkbox } from './checkbox'

/**
 * The indicator stacks both glyphs and hides one with a utility class, so the
 * cascade — not the markup — decides what the user sees: the `group-data-*`
 * selector's higher specificity beats the bare `hidden!` utility even though
 * both carry `!important`. That specificity race is the real contract, so the
 * test carries the stylesheet rather than asserting on class strings alone.
 * Tailwind's nested output is flattened to the equivalent descendant selector
 * because jsdom does not implement CSS nesting.
 */
const TAILWIND_CSS = `
  .hidden\\! { display: none !important; }
  :where(.group)[data-state="checked"] .group-data-\\[state\\=checked\\]\\:block\\! {
    display: block !important;
  }
  :where(.group)[data-state="indeterminate"] .group-data-\\[state\\=indeterminate\\]\\:block\\! {
    display: block !important;
  }
`

function shownGlyphs(container: HTMLElement) {
  return [...container.querySelectorAll<HTMLElement>('svg[data-codicon]')]
    .filter(glyph => getComputedStyle(glyph).display !== 'none')
    .map(glyph => glyph.getAttribute('data-codicon'))
}

beforeAll(() => {
  // eslint-disable-next-line no-restricted-globals -- the cascade is the assertion; it needs a real stylesheet
  const style = document.createElement('style')
  style.textContent = TAILWIND_CSS
  // eslint-disable-next-line no-restricted-globals -- see above
  document.head.append(style)
})

afterEach(cleanup)

describe('Checkbox', () => {
  it('paints the check alone when checked', () => {
    const { container } = render(<Checkbox checked />)

    expect(shownGlyphs(container)).toEqual(['check'])
  })

  it('paints the dash alone when indeterminate', () => {
    const { container } = render(<Checkbox checked="indeterminate" />)

    expect(shownGlyphs(container)).toEqual(['dash'])
  })

  it('paints no glyph when unchecked', () => {
    const { container } = render(<Checkbox checked={false} />)

    expect(shownGlyphs(container)).toEqual([])
  })
})
