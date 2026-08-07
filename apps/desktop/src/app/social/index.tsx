'use client'

import { useState } from 'react'

import { PremiumGate } from '@/components/premium-gate'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  preventCloseButtonAutoFocus
} from '@/components/ui/dialog'
import { updateSocialPlatform } from '@/hermes'
import { useI18n } from '@/i18n'
import { Eye } from '@/lib/icons'
import { readableError } from '@/store/notifications'

import { Panel, PanelHeader } from '../overlays/panel'
import { ListRow } from '../settings/primitives'

import { SocialApprovalCard } from './approval-card'
import { ConnectionWizard, type StepValidationResult } from './connection-wizard'
import {
  connectionFor,
  MOCK_APPROVAL_PREVIEW,
  MOCK_SOCIAL_CONNECTIONS,
  MOCK_WIZARD_STEPS,
  SOCIAL_NETWORKS,
  type SocialAccountConnection,
  type SocialConnectionStatus,
  type SocialNetworkId
} from './fixtures'
import { NETWORK_ICONS } from './network-icons'

interface SocialViewProps {
  onClose: () => void
}

const STATUS_BADGE_VARIANT: Record<SocialConnectionStatus, 'default' | 'destructive' | 'muted' | 'warn'> = {
  connected: 'default',
  token_expiring: 'warn',
  error: 'destructive',
  disconnected: 'muted'
}

function StatusBadge({ connection }: { connection: SocialAccountConnection }) {
  const { t } = useI18n()

  const label = {
    connected: t.social.statusConnected,
    token_expiring: t.social.statusTokenExpiring,
    error: t.social.statusError,
    disconnected: t.social.statusDisconnected
  }[connection.status]

  return <Badge variant={STATUS_BADGE_VARIANT[connection.status]}>{label}</Badge>
}

function NetworkRow({
  connection,
  onConnect
}: {
  connection: SocialAccountConnection
  onConnect: (network: SocialNetworkId) => void
}) {
  const { t } = useI18n()
  const Icon = NETWORK_ICONS[connection.network]
  const label = t.social.networks[connection.network] ?? connection.network

  const actionLabel =
    connection.status === 'disconnected'
      ? t.social.connect
      : connection.status === 'connected'
        ? t.social.manage
        : t.social.reconnect

  return (
    <ListRow
      action={
        <Button
          onClick={() => onConnect(connection.network)}
          size="sm"
          variant={connection.status === 'disconnected' ? 'default' : 'secondary'}
        >
          {actionLabel}
        </Button>
      }
      description={
        connection.status === 'error'
          ? connection.errorDetail
          : connection.accountHandle
            ? connection.accountHandle
            : undefined
      }
      title={
        <span className="flex items-center gap-2">
          <Icon className="size-4 shrink-0 text-(--ui-text-secondary)" />
          {label}
          <StatusBadge connection={connection} />
        </span>
      }
    />
  )
}

// Etapa A frontend (douglas/CORE_PATCHES.md) + Fase B1's first real backend
// wiring, Facebook only (douglas/IMPLEMENTATION_PLAN.md, "Modulo Social").
// Every other network, and Facebook's final "permissions" step, are still
// entirely mocked.
const FACEBOOK_STEP_ENV_KEY: Record<string, string> = {
  'app-id': 'FACEBOOK_APP_ID',
  'app-secret': 'FACEBOOK_APP_SECRET',
  'page-id': 'FACEBOOK_PAGE_ID'
}

async function validateFacebookStep(stepId: string, value: string): Promise<StepValidationResult> {
  const envKey = FACEBOOK_STEP_ENV_KEY[stepId]

  // The final 'permissions' step is real OAuth (Fase B2 — not built yet).
  // Let it through unmodified so the wizard's mocked-success path still
  // covers it, same as every still-fully-mocked network.
  if (!envKey) {
    return { ok: true }
  }

  try {
    await updateSocialPlatform('facebook', { env: { [envKey]: value } })

    return { ok: true }
  } catch (err) {
    return { ok: false, error: readableError(err, 'No se pudo guardar la credencial.').message }
  }
}

export function SocialView({ onClose }: SocialViewProps) {
  const { t } = useI18n()
  const [wizardNetwork, setWizardNetwork] = useState<SocialNetworkId | null>(null)
  const [previewOpen, setPreviewOpen] = useState(false)

  return (
    <Panel onClose={onClose}>
      <PanelHeader
        actions={
          <Button onClick={() => setPreviewOpen(true)} size="sm" variant="ghost">
            <Eye className="size-3.5" />
            {t.social.approvalPreviewButton}
          </Button>
        }
        subtitle={t.social.panelSubtitle}
        title={t.social.panelTitle}
      />
      <div className="min-h-0 flex-1 overflow-y-auto">
        <PremiumGate>
          <div className="flex flex-col divide-y divide-(--ui-stroke-secondary)">
            {SOCIAL_NETWORKS.map(network => (
              <NetworkRow
                connection={connectionFor(network, MOCK_SOCIAL_CONNECTIONS)}
                key={network}
                onConnect={setWizardNetwork}
              />
            ))}
          </div>
        </PremiumGate>
      </div>

      <Dialog onOpenChange={open => !open && setWizardNetwork(null)} open={wizardNetwork !== null}>
        <DialogContent onOpenAutoFocus={preventCloseButtonAutoFocus}>
          {wizardNetwork && (
            <>
              <DialogHeader>
                <DialogTitle>{t.social.wizardTitle(t.social.networks[wizardNetwork] ?? wizardNetwork)}</DialogTitle>
              </DialogHeader>
              <ConnectionWizard
                networkLabel={t.social.networks[wizardNetwork] ?? wizardNetwork}
                onCancel={() => setWizardNetwork(null)}
                onDone={() => setWizardNetwork(null)}
                onValidateStep={wizardNetwork === 'facebook' ? validateFacebookStep : undefined}
                steps={MOCK_WIZARD_STEPS[wizardNetwork]}
              />
            </>
          )}
        </DialogContent>
      </Dialog>

      <Dialog onOpenChange={setPreviewOpen} open={previewOpen}>
        <DialogContent fitContent onOpenAutoFocus={preventCloseButtonAutoFocus}>
          <DialogHeader className="sr-only">
            <DialogTitle>{t.social.approvalPreviewButton}</DialogTitle>
            <DialogDescription>{t.social.approvalTitle}</DialogDescription>
          </DialogHeader>
          <SocialApprovalCard
            onApprove={() => setPreviewOpen(false)}
            onDiscard={() => setPreviewOpen(false)}
            onEdit={() => setPreviewOpen(false)}
            preview={MOCK_APPROVAL_PREVIEW}
          />
        </DialogContent>
      </Dialog>
    </Panel>
  )
}
