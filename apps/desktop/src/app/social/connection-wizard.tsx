'use client'

import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Field, FieldHint } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { useI18n } from '@/i18n'
import { AlertCircle, Check, CheckCircle2, Loader2 } from '@/lib/icons'
import { cn } from '@/lib/utils'

import type { WizardStepDefinition, WizardStepStatus } from './fixtures'

interface ConnectionWizardProps {
  networkLabel: string
  steps: readonly WizardStepDefinition[]
  onCancel: () => void
  onDone: () => void
}

// Step-by-step connector, content-only (no dialog/modal chrome of its own) so
// it can be dropped into a Dialog today and into a chat bubble later without
// a rewrite — see douglas/PLAN-CAPA-SOCIAL.md Etapa A2: "diseñado para
// invocarse DESDE EL CHAT, no como wizard aislado".
//
// Validation is entirely mocked: it always succeeds after a short simulated
// round trip. The real per-network step CONTENT (what to actually ask/check)
// is deliberately not hardcoded here — it comes from `steps`, sourced in
// fixtures.ts today and from the user's real Meta-connection walkthrough in a
// later session.
export function ConnectionWizard({ networkLabel, steps, onCancel, onDone }: ConnectionWizardProps) {
  const { t } = useI18n()
  const [stepIndex, setStepIndex] = useState(0)
  const [stepStatus, setStepStatus] = useState<WizardStepStatus>('current')
  const [validating, setValidating] = useState(false)
  const [inputValue, setInputValue] = useState('')
  const [errorText, setErrorText] = useState<string | null>(null)

  const step = steps[stepIndex]
  const isLastStep = stepIndex === steps.length - 1

  function statusFor(index: number): WizardStepStatus {
    if (index < stepIndex) {
      return 'done'
    }

    if (index === stepIndex) {
      return stepStatus
    }

    return 'pending'
  }

  function validate() {
    if (step.hasInput && !inputValue.trim()) {
      setErrorText(t.social.wizardFieldRequired)
      setStepStatus('error')

      return
    }

    setErrorText(null)
    setValidating(true)

    // Mocked round trip — Etapa B replaces this with a real call against
    // douglas/plugins/social_auth's per-step validator.
    window.setTimeout(() => {
      setValidating(false)
      setStepStatus('done')

      if (isLastStep) {
        onDone()

        return
      }

      setStepIndex(i => i + 1)
      setStepStatus('current')
      setInputValue('')
    }, 400)
  }

  return (
    <div className="flex flex-col gap-4" data-slot="social-connection-wizard">
      <ol className="flex flex-col gap-0.5">
        {steps.map((s, index) => {
          const status = statusFor(index)

          return (
            <li className="flex items-start gap-2.5 px-1 py-1.5" key={s.id}>
              <span className="mt-0.5 flex size-4 shrink-0 items-center justify-center">
                {status === 'done' && <CheckCircle2 className="size-4 text-primary" />}
                {status === 'current' && <div className="size-2 rounded-full bg-primary" />}
                {status === 'error' && <AlertCircle className="size-4 text-destructive" />}
                {status === 'pending' && <div className="size-1.5 rounded-full border border-(--ui-stroke-secondary)" />}
              </span>
              <div className="min-w-0 flex-1">
                <div
                  className={cn(
                    'text-[length:var(--conversation-text-font-size)]',
                    status === 'current' ? 'font-medium text-foreground' : 'text-(--ui-text-secondary)',
                    status === 'pending' && 'text-muted-foreground/60'
                  )}
                >
                  {s.title}
                </div>
                {status === 'current' && (
                  <div className="mt-1 flex flex-col gap-2">
                    <p className="text-[length:var(--conversation-caption-font-size)] text-(--ui-text-tertiary)">
                      {s.instruction}
                    </p>
                    {s.hasInput && (
                      <Field label={s.inputLabel}>
                        <Input
                          onChange={e => setInputValue(e.target.value)}
                          placeholder={s.inputPlaceholder}
                          value={inputValue}
                        />
                        {errorText && <FieldHint error>{errorText}</FieldHint>}
                      </Field>
                    )}
                    {!s.hasInput && errorText && <p className="text-xs text-destructive">{errorText}</p>}
                  </div>
                )}
              </div>
            </li>
          )
        })}
      </ol>

      <div className="flex justify-end gap-2">
        <Button onClick={onCancel} variant="ghost">
          {t.social.wizardCancel}
        </Button>
        <Button disabled={validating} onClick={validate}>
          {validating ? (
            <>
              <Loader2 className="size-3.5 animate-spin" />
              {t.social.wizardValidating}
            </>
          ) : isLastStep ? (
            <>
              <Check className="size-3.5" />
              {t.social.wizardValidate}
            </>
          ) : (
            t.social.wizardNext
          )}
        </Button>
      </div>
    </div>
  )
}
