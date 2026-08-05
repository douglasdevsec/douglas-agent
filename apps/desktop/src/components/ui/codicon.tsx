import type { Icon, IconProps } from '@tabler/icons-react'
import { IconShape } from '@tabler/icons-react'

import { cn } from '@/lib/utils'

import { CODICON_GLYPHS } from './codicon-glyphs'

export interface CodiconProps extends Omit<IconProps, 'children' | 'name'> {
  name: string
  spinning?: boolean
}

/**
 * Renders Douglas Agent's icon vocabulary. `name` is still the codicon
 * identifier used throughout the app's data (project/profile pickers,
 * reference styles, etc.) — it's looked up in {@link CODICON_GLYPHS} and
 * rendered as a Tabler icon rather than the inherited VS Code glyph font.
 * An unmapped name falls back to a generic glyph instead of rendering
 * nothing, so a missed mapping is visible but never breaks layout.
 */
export function Codicon({ className, name, size, spinning, style, ...props }: CodiconProps) {
  const Glyph = CODICON_GLYPHS[name] ?? IconShape

  return (
    <Glyph
      aria-hidden="true"
      className={cn('shrink-0', spinning && 'animate-spin', className)}
      // The codicon identifier survives independently of which Tabler icon
      // backs it, so callers (and tests) can key off the semantic name
      // instead of an implementation detail that's free to change.
      data-codicon={name}
      // `size` always sets the width/height ATTRIBUTE (falling back to 1em, so
      // an unsized glyph still scales with its own font-size like the old font
      // icon did) — low precedence, so a `size-*` Tailwind class or a Button
      // ancestor's `[&_svg:not([class*='size-'])]:size-*` rule can still win.
      // Only an EXPLICIT `size` prop is also forced via inline style, which no
      // class-based rule can outrank, matching the old `style.fontSize` default.
      size={size ?? '1em'}
      style={size === undefined ? style : { height: size, width: size, ...style }}
      {...props}
    />
  )
}

/** Wrap a codicon as a Tabler-shaped icon for nav rows that expect `IconComponent`. */
export function codiconIcon(name: string): Icon {
  function CodiconIcon({ className }: { className?: string }) {
    return <Codicon aria-hidden className={cn('leading-none', className)} name={name} size="1em" />
  }

  CodiconIcon.displayName = `Codicon(${name})`

  return CodiconIcon as Icon
}
