'use client'

import { useNavigate } from 'react-router'

import { PremiumGate } from '@/components/premium-gate'
import { useI18n } from '@/i18n'

import { SOCIAL_ROUTE } from '../routes'

import { SOCIAL_NETWORKS } from './fixtures'
import { NETWORK_ICONS } from './network-icons'

// Discoverability teaser for the chat home screen — a row of network icons
// that draws attention to the social layer, distinct from the full status
// panel at /social (app/social/index.tsx). Free users see the same icons
// (that's the point — they should notice the feature) but tapping one opens
// the upsell instead of the connect flow; premium users go straight to the
// config panel. Gated as one unit via PremiumGate, matching the panel's own
// gating so the two surfaces never disagree about who's premium.
export function SocialHomeTeaser() {
  const { t } = useI18n()
  const navigate = useNavigate()

  return (
    <PremiumGate className="inline-block w-auto">
      <div className="flex items-center gap-2.5" data-slot="social-home-teaser">
        {SOCIAL_NETWORKS.map(network => {
          const Icon = NETWORK_ICONS[network]
          const label = `${t.social.connect} ${t.social.networks[network] ?? network}`

          return (
            <button
              aria-label={label}
              className="flex size-8 items-center justify-center rounded-full text-(--ui-text-tertiary) transition-colors hover:bg-(--chrome-action-hover) hover:text-foreground"
              key={network}
              onClick={() => navigate(SOCIAL_ROUTE)}
              title={label}
              type="button"
            >
              <Icon className="size-4" />
            </button>
          )
        })}
      </div>
    </PremiumGate>
  )
}
