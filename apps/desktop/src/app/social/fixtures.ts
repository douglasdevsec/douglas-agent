// Mocked data for the Etapa A social layer (see douglas/CORE_PATCHES.md) —
// still true for every network except Facebook's 4 wizard steps below,
// which now call a real backend end to end: credentials
// (hermes_cli/social_platforms.py) and OAuth authorization
// (hermes_cli/social_oauth.py), both via connection-wizard.tsx's
// onValidateStep. The `MOCK_SOCIAL_CONNECTIONS` status list below is still
// entirely mocked for all networks, Facebook included — see
// douglas/IMPLEMENTATION_PLAN.md, "Modulo Social", Fase B4.

export type SocialNetworkId = 'facebook' | 'instagram' | 'linkedin' | 'tiktok' | 'x' | 'youtube'

export const SOCIAL_NETWORKS: readonly SocialNetworkId[] = [
  'facebook',
  'instagram',
  'youtube',
  'linkedin',
  'tiktok',
  'x'
]

export type SocialConnectionStatus = 'connected' | 'disconnected' | 'error' | 'token_expiring'

export interface SocialAccountConnection {
  network: SocialNetworkId
  status: SocialConnectionStatus
  accountName?: string
  accountHandle?: string
  /** ISO timestamp. Only meaningful when status is 'token_expiring'. */
  tokenExpiresAt?: string
  /** Human-readable cause. Only meaningful when status is 'error'. */
  errorDetail?: string
}

// A realistic mixed state — one of each status — so the panel's every visual
// branch is exercised just by opening it, no interaction needed.
export const MOCK_SOCIAL_CONNECTIONS: readonly SocialAccountConnection[] = [
  { network: 'instagram', status: 'connected', accountName: 'Douglas Agent', accountHandle: '@douglasagent' },
  {
    network: 'facebook',
    status: 'token_expiring',
    accountName: 'Douglas Agent',
    tokenExpiresAt: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString()
  },
  { network: 'youtube', status: 'error', errorDetail: 'Refresh token was revoked outside Douglas Agent.' },
  { network: 'linkedin', status: 'disconnected' },
  { network: 'tiktok', status: 'disconnected' },
  { network: 'x', status: 'disconnected' }
]

export function connectionFor(
  network: SocialNetworkId,
  connections: readonly SocialAccountConnection[] = MOCK_SOCIAL_CONNECTIONS
): SocialAccountConnection {
  return connections.find(c => c.network === network) ?? { network, status: 'disconnected' }
}

// ── Connection wizard ────────────────────────────────────────────────────
// Parameterized by data, not hardcoded per network — the real per-step
// instructions for Meta come from the user's own hands-on connection
// experience (see douglas/PLAN-CAPA-SOCIAL.md, Etapa A2). This mock fixture
// stands in for that until then.

export type WizardStepStatus = 'current' | 'done' | 'error' | 'pending'

export interface WizardStepDefinition {
  id: string
  title: string
  instruction: string
  /** Whether this step collects a value (API key, page id, ...) before validating. */
  hasInput?: boolean
  inputLabel?: string
  inputPlaceholder?: string
}

export const MOCK_WIZARD_STEPS: Record<SocialNetworkId, readonly WizardStepDefinition[]> = {
  // Every Facebook step is real (see connection-wizard.tsx's
  // onValidateStep + hermes.ts's updateSocialPlatform/startFacebookOAuth/
  // getFacebookOAuthStatus) — every user brings their OWN Meta developer
  // app, never a Douglas-owned one shared across installs, so credentials
  // are collected here rather than via a centralized OAuth "just
  // authorize" flow. See douglas/PROGRESS.md (2026-08-07 entries, Fase B1
  // + B2) for the product decision.
  facebook: [
    {
      id: 'app-id',
      title: 'App ID de Meta',
      instruction:
        'Pega el App ID de tu propia app de Meta for Developers. Antes de continuar, agrega ' +
        'http://localhost:53682/facebook/callback a "Valid OAuth Redirect URIs" en la ' +
        'configuración de Facebook Login for Business de esa app — solo hace falta una vez.',
      hasInput: true,
      inputLabel: 'App ID',
      inputPlaceholder: '1234567890123456'
    },
    {
      id: 'app-secret',
      title: 'App Secret de Meta',
      instruction: 'Pega el App Secret de esa misma app. Se guarda solo en tu equipo.',
      hasInput: true,
      inputLabel: 'App Secret',
      inputPlaceholder: 'a1b2c3d4e5f6...'
    },
    {
      id: 'page-id',
      title: 'Página vinculada',
      instruction: 'Pega el ID de la página que quieres conectar. Tu usuario de Facebook debe ser administrador de esa página.',
      hasInput: true,
      inputLabel: 'ID de página',
      inputPlaceholder: '1234567890'
    },
    {
      id: 'permissions',
      title: 'Permisos',
      instruction:
        'Se abrirá tu navegador para autorizar a Douglas Agent a publicar en tu nombre. ' +
        'Vuelve a esta ventana cuando termines — puede tardar unos segundos en confirmarse.'
    }
  ],
  instagram: [
    { id: 'business-account', title: 'Cuenta profesional', instruction: 'Confirma que tu Instagram es una cuenta de empresa o creador.' },
    { id: 'linked-page', title: 'Página de Facebook vinculada', instruction: 'Instagram requiere una página de Facebook vinculada.' },
    { id: 'permissions', title: 'Permisos', instruction: 'Autoriza a Douglas Agent a publicar en tu nombre.' }
  ],
  youtube: [
    { id: 'channel', title: 'Canal', instruction: 'Confirma el canal de YouTube que quieres conectar.' },
    { id: 'oauth', title: 'Autorización de Google', instruction: 'Inicia sesión con la cuenta de Google del canal.' }
  ],
  linkedin: [
    { id: 'page', title: 'Página de empresa', instruction: 'Confirma la página de empresa de LinkedIn a conectar.' },
    { id: 'oauth', title: 'Autorización', instruction: 'Autoriza a Douglas Agent desde LinkedIn.' }
  ],
  tiktok: [
    { id: 'business-account', title: 'Cuenta profesional', instruction: 'Confirma que tienes una cuenta TikTok Business.' },
    { id: 'oauth', title: 'Autorización', instruction: 'Autoriza a Douglas Agent desde TikTok.' }
  ],
  x: [{ id: 'oauth', title: 'Autorización', instruction: 'Autoriza a Douglas Agent desde X (Twitter).' }]
}

// ── Approval card ────────────────────────────────────────────────────────

export interface SocialApprovalPreview {
  mediaUrl?: string
  mediaKind?: 'image' | 'video'
  copy: string
  hashtags: readonly string[]
  networks: readonly SocialNetworkId[]
  scheduledFor?: string
  autoPublishDefault?: boolean
}

export const MOCK_APPROVAL_PREVIEW: SocialApprovalPreview = {
  mediaKind: 'image',
  copy: 'Esta semana el producto más vendido fue nuestro set de bienvenida — gracias por tanto cariño 💚',
  hashtags: ['#DouglasAgent', '#hechoconIA', '#pyme'],
  networks: ['instagram', 'facebook'],
  scheduledFor: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString(),
  autoPublishDefault: false
}
