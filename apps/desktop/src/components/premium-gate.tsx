'use client'

import { useState } from 'react'
import type { ReactNode } from 'react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  preventCloseButtonAutoFocus
} from '@/components/ui/dialog'
import { useI18n } from '@/i18n'
import { Lock } from '@/lib/icons'
import { cn } from '@/lib/utils'

// Single mocked decision point for "is this user premium". Every
// premium-gated surface in the app should import isPremiumUser from here
// rather than rolling its own check, so swapping in the real
// billing/entitlement read later (Etapa B+) is a one-file change.
export function isPremiumUser(): boolean {
  return false
}

interface PremiumGateProps {
  children: ReactNode
  className?: string
}

// Wraps any premium feature: renders `children` normally for a premium user,
// otherwise dims them, adds a lock affordance, and opens an upsell dialog on
// click instead of letting the interaction through. Reusable across every
// paid surface — see douglas/CORE_PATCHES.md for where this is used first
// (the social network config panel).
export function PremiumGate({ children, className }: PremiumGateProps) {
  const { t } = useI18n()
  const [upsellOpen, setUpsellOpen] = useState(false)

  if (isPremiumUser()) {
    return <>{children}</>
  }

  return (
    <>
      <button
        aria-label={t.social.premiumLocked}
        className={cn('group relative block w-full rounded-md text-left', className)}
        onClick={() => setUpsellOpen(true)}
        type="button"
      >
        <div aria-hidden className="pointer-events-none opacity-55 grayscale-[35%]">
          {children}
        </div>
        <div className="absolute inset-0 flex items-center justify-center rounded-md bg-background/35 opacity-0 transition-opacity group-hover:opacity-100">
          <Lock className="size-4 text-muted-foreground" />
        </div>
      </button>

      <Dialog onOpenChange={setUpsellOpen} open={upsellOpen}>
        <DialogContent onOpenAutoFocus={preventCloseButtonAutoFocus}>
          <DialogHeader>
            <DialogTitle icon={Lock}>{t.social.premiumUpgradeTitle}</DialogTitle>
            <DialogDescription>{t.social.premiumUpgradeBody}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button onClick={() => setUpsellOpen(false)} variant="ghost">
              {t.social.premiumMaybeLater}
            </Button>
            <Button onClick={() => setUpsellOpen(false)}>{t.social.premiumUpgradeCta}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
