'use client'

import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Field, FieldHint } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { useI18n } from '@/i18n'
import { AlertCircle, Check, CheckCircle2, Loader2 } from '@/lib/icons'
import { cn } from '@/lib/utils'

import type { WizardStepDefinition, WizardStepStatus } from './fixtures'

export interface StepValidationResult {
  error?: string
  ok: boolean
}

interface ConnectionWizardProps {
  networkLabel: string
  /**
   * Real per-step validator, called instead of the mocked round trip below
   * for steps this network has wired to a real backend. Omit to keep every
   * step mocked (still the default for every network except Facebook's
   * credential-entry steps — see index.tsx). Steps this function doesn't
   * recognize should still resolve `{ ok: true }` so the rest of a
   * network's flow (e.g. Facebook's still-mocked final "permissions" step)
   * keeps working exactly as before.
   */
  onValidateStep?: (stepId: string, value: string) => Promise<StepValidationResult>
  onCancel: () => void
  onDone: () => void
  steps: readonly WizardStepDefinition[]
}

// Step-by-step connector, content-only (no dialog/modal chrome of its own) so
// it can be dropped into a Dialog today and into a chat bubble later without
// a rewrite — designed to eventually be invocable from the chat, not just as
// a standalone wizard.
//
// Validation is mocked by default (always succeeds after a short simulated
// round trip) unless the caller passes `onValidateStep` for a real backend
// call — see Facebook's credential-entry steps in index.tsx for the first
// real one. The per-network step CONTENT (what to actually ask/check) is
// deliberately not hardcoded here — it comes from `steps`, sourced in
// fixtures.ts.
export function ConnectionWizard({ networkLabel, onCancel, onDone, onValidateStep, steps }: ConnectionWizardProps) {
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

  function advance() {
    setValidating(false)
    setStepStatus('done')

    if (isLastStep) {
      onDone()

      return
    }

    setStepIndex(i => i + 1)
    setStepStatus('current')
    setInputValue('')
  }

  async function validate() {
    if (step.hasInput && !inputValue.trim()) {
      setErrorText(t.social.wizardFieldRequired)
      setStepStatus('error')

      return
    }

    setErrorText(null)
    setValidating(true)

    if (onValidateStep) {
      const result = await onValidateStep(step.id, inputValue)

      if (!result.ok) {
        setValidating(false)
        setErrorText(result.error ?? t.social.wizardFieldRequired)
        setStepStatus('error')

        return
      }

      advance()

      return
    }

    // Mocked round trip for every step this network hasn't wired to a real
    // backend yet.
    window.setTimeout(advance, 400)
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
