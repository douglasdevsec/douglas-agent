'use client'

import { useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { useI18n } from '@/i18n'
import { Clock, Pencil, Send, Trash2 } from '@/lib/icons'
import { cn } from '@/lib/utils'

import type { SocialApprovalPreview } from './fixtures'
import { NETWORK_ICONS } from './network-icons'

interface SocialApprovalCardProps {
  preview: SocialApprovalPreview
  onApprove: (autoPublish: boolean) => void
  onDiscard: () => void
  onEdit: () => void
}

// Rendered inside the chat thread. Registered as a tool-card in
// components/assistant-ui/thread/message-parts.tsx (ChainToolFallback) under
// the 'social_publish' toolName, following the exact pattern
// components/assistant-ui/tool/approval.tsx uses for command-execution
// approvals — see douglas/CORE_PATCHES.md.
//
// Etapa A has no backend, so nothing emits a real 'social_publish' tool call
// yet: this component is exercised via the "Vista previa" button in the
// social config panel (app/social/index.tsx), which mounts it with mock data
// in a Dialog. The in-thread registration is real and ready for Etapa C to
// drive with a live tool call — only the trigger is mocked, not the render
// path.
export function SocialApprovalCard({ preview, onApprove, onDiscard, onEdit }: SocialApprovalCardProps) {
  const { t } = useI18n()
  const [autoPublish, setAutoPublish] = useState(Boolean(preview.autoPublishDefault))

  const scheduled = preview.scheduledFor ? new Date(preview.scheduledFor) : null

  return (
    <div
      className="flex max-w-md flex-col gap-3 rounded-xl border border-(--stroke-nous) bg-(--ui-chat-bubble-background) p-3.5 shadow-nous"
      data-slot="social-approval-card"
    >
      <div className="flex items-center gap-2">
        <Send className="size-4 shrink-0 text-primary" />
        <span className="text-[0.9375rem] font-semibold tracking-tight text-foreground">{t.social.approvalTitle}</span>
      </div>

      {preview.mediaKind && (
        <div className="flex aspect-video items-center justify-center rounded-lg border border-dashed border-(--ui-stroke-secondary) bg-(--ui-bg-tertiary) text-[0.7rem] text-muted-foreground">
          {preview.mediaKind === 'video' ? 'Video preview' : 'Image preview'}
        </div>
      )}

      <p className="text-[length:var(--conversation-text-font-size)] leading-relaxed whitespace-pre-wrap text-foreground">
        {preview.copy}
      </p>

      {preview.hashtags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {preview.hashtags.map(tag => (
            <Badge key={tag} variant="muted">
              {tag}
            </Badge>
          ))}
        </div>
      )}

      <div className="flex flex-col gap-1.5 border-t border-(--ui-stroke-secondary) pt-2.5 text-[length:var(--conversation-caption-font-size)]">
        <div className="flex items-center gap-2">
          <span className="w-20 shrink-0 text-(--ui-text-tertiary)">{t.social.approvalDestination}</span>
          <div className="flex items-center gap-1.5">
            {preview.networks.map(network => {
              const Icon = NETWORK_ICONS[network]

              return <Icon className="size-3.5 text-(--ui-text-secondary)" key={network} />
            })}
          </div>
        </div>
        <div className="flex items-center gap-2 text-(--ui-text-tertiary)">
          <Clock className="size-3.5 shrink-0" />
          <span>
            {scheduled
              ? t.social.approvalScheduledFor(
                  scheduled.toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
                )
              : t.social.approvalPublishNow}
          </span>
        </div>
      </div>

      <label className="flex cursor-pointer items-start gap-2 text-[length:var(--conversation-caption-font-size)] text-(--ui-text-secondary)">
        <Checkbox checked={autoPublish} className="mt-0.5" onCheckedChange={value => setAutoPublish(value === true)} />
        <span>
          {t.social.approvalAutoPublish}
          <span className="block text-[0.68rem] text-muted-foreground/70">{t.social.approvalAutoPublishNote}</span>
        </span>
      </label>

      <div className="flex justify-end gap-2">
        <Button className={cn('text-destructive hover:text-destructive')} onClick={onDiscard} variant="ghost">
          <Trash2 className="size-3.5" />
          {t.social.approvalDiscard}
        </Button>
        <Button onClick={onEdit} variant="secondary">
          <Pencil className="size-3.5" />
          {t.social.approvalEdit}
        </Button>
        <Button onClick={() => onApprove(autoPublish)}>{t.social.approvalApprove}</Button>
      </div>
    </div>
  )
}
