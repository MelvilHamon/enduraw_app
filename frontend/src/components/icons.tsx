// Placeholder line-icons for the bottom nav, one per tab. Deliberately simple
// 24px stroke glyphs so they read at small sizes and inherit `currentColor`.
// These are swap targets: when the per-tab logo images arrive, replace the
// matching component body (keep the `IconProps` contract).

import type { ReactNode, SVGProps } from "react";

export type IconProps = SVGProps<SVGSVGElement>;

function Base({ children, ...props }: IconProps & { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      width={22}
      height={22}
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  );
}

// Accueil — home / overview.
export function HomeIcon(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M3 10.5 12 4l9 6.5" />
      <path d="M5 9.5V20h14V9.5" />
      <path d="M9.5 20v-5h5v5" />
    </Base>
  );
}

// Charge — training load / trend.
export function LoadIcon(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M4 19V5" />
      <path d="M4 19h16" />
      <path d="m7 14 3.5-4 3 2.5L20 6" />
    </Base>
  );
}

// Routine — daily check-in (target / tap).
export function RoutineIcon(props: IconProps) {
  return (
    <Base {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="12" cy="12" r="0.6" fill="currentColor" />
    </Base>
  );
}

// Santé — health (heart pulse).
export function HealthIcon(props: IconProps) {
  return (
    <Base {...props}>
      <path d="M3 12h3l2-5 3 10 2.5-7L18 12h3" />
    </Base>
  );
}

// Profil — user.
export function ProfileIcon(props: IconProps) {
  return (
    <Base {...props}>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M5 20a7 7 0 0 1 14 0" />
    </Base>
  );
}

// Settings — gear (profile sub-page entry).
export function SettingsIcon(props: IconProps) {
  return (
    <Base {...props}>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2.5v3M12 18.5v3M21.5 12h-3M5.5 12h-3M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1M18.4 18.4l-2.1-2.1M7.7 7.7 5.6 5.6" />
    </Base>
  );
}
