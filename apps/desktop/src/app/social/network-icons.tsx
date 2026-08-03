import { SiFacebook, SiInstagram, SiTiktok, SiX, SiYoutube } from '@icons-pack/react-simple-icons'
import { IconBrandLinkedin } from '@tabler/icons-react'
import type { ComponentType, SVGProps } from 'react'

import type { SocialNetworkId } from './fixtures'

type NetworkIcon = ComponentType<SVGProps<SVGSVGElement> & { title?: string }>

// Simple Icons (already a dependency — see lib/brand-icon.ts) covers 5 of 6.
// LinkedIn is deliberately absent from Simple Icons at the trademark owner's
// request (same note in lib/brand-icon.ts), so it comes from Tabler instead
// (@tabler/icons-react, also already a dependency) — the only mixed-source
// entry in this map.
export const NETWORK_ICONS: Record<SocialNetworkId, NetworkIcon> = {
  facebook: SiFacebook,
  instagram: SiInstagram,
  youtube: SiYoutube,
  linkedin: IconBrandLinkedin as unknown as NetworkIcon,
  tiktok: SiTiktok,
  x: SiX
}
