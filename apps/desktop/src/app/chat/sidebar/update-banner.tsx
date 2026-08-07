'use client'

import { useStore } from '@nanostores/react'

import logoBlack from '@/assets/brand/logo_black.png'
import logoWhite from '@/assets/brand/logo_white.png'
import { useI18n } from '@/i18n'
import { ChevronRight } from '@/lib/icons'
import { $desktopVersion, $updateApply, $updateStatus, startActiveUpdate } from '@/store/updates'
import { useTheme } from '@/themes/context'

// High-visibility home-sidebar CTA, distinct from (and in addition to) the
// About page's own update controls (settings/about-settings.tsx, never
// touched by this) — most users never open Settings > About, so the only
// place they'd otherwise learn an update is ready is a toast they may have
// dismissed. Reuses the exact same $updateStatus/startActiveUpdate the
// About page already drives, so the two surfaces can never disagree.
//
// Client-desktop-update only (not $backendUpdateStatus/remote mode) — this
// lives in the always-visible home sidebar, which only makes sense for the
// app the user is looking at right now.
export function SidebarUpdateBanner() {
  const { t } = useI18n()
  const s = t.sidebar.updateBanner
  const status = useStore($updateStatus)
  const apply = useStore($updateApply)
  const version = useStore($desktopVersion)
  const { renderedMode } = useTheme()

  const behind = status?.behind ?? 0
  const supported = status?.supported !== false
  const applying = apply.applying || apply.stage === 'restart'

  if (behind <= 0 || !supported || applying) {
    return null
  }

  // Keyed off renderedMode (what's actually painted), not the user's raw
  // light/dark preference — a skin that keeps a bright surface under "dark"
  // would otherwise pick the wrong logo variant for the real background.
  const logo = renderedMode === 'dark' ? logoWhite : logoBlack

  return (
    <button
      className="flex h-11 w-full shrink-0 items-center gap-2.5 rounded-md border border-primary/30 bg-primary/5 px-2.5 text-left transition-colors duration-100 ease-out hover:border-primary/45 hover:bg-primary/10 [-webkit-app-region:no-drag]"
      onClick={() => startActiveUpdate()}
      type="button"
    >
      <img alt="" aria-hidden className="size-6 shrink-0 object-contain" src={logo} />
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[0.8125rem] font-medium text-foreground">{s.restartToUpdate}</span>
        {version?.appVersion && (
          <span className="block truncate text-xs text-muted-foreground">{s.version(version.appVersion)}</span>
        )}
      </span>
      <ChevronRight className="size-4 shrink-0 text-primary" />
    </button>
  )
}
