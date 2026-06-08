import { NavLink } from "react-router-dom";
import {
  HealthIcon,
  HomeIcon,
  LoadIcon,
  ProfileIcon,
  RoutineIcon,
  type IconProps,
} from "./icons";

type Item = { to: string; label: string; Icon: (p: IconProps) => JSX.Element };

// The five product tabs. `Icon` placeholders live in components/icons.tsx and
// are the swap target once per-tab logo images are provided.
const ITEMS: Item[] = [
  { to: "/home", label: "Accueil", Icon: HomeIcon },
  { to: "/load", label: "Charge", Icon: LoadIcon },
  { to: "/routine", label: "Routine", Icon: RoutineIcon },
  { to: "/health", label: "Santé", Icon: HealthIcon },
  { to: "/profile", label: "Profil", Icon: ProfileIcon },
];

export function BottomNav() {
  return (
    <nav className="sticky bottom-0 z-10 grid grid-cols-5 border-t border-ink-600 bg-ink-950/95 pb-[env(safe-area-inset-bottom)] backdrop-blur">
      {ITEMS.map(({ to, label, Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            `relative flex flex-col items-center gap-1 py-2.5 text-[10px] font-semibold uppercase tracking-[0.06em] transition-colors ${
              isActive ? "text-flame-500" : "text-stone-500 hover:text-stone-300"
            }`
          }
        >
          {({ isActive }) => (
            <>
              {isActive && (
                <span className="absolute top-0 h-0.5 w-8 rounded-full bg-flame-500 shadow-glow" />
              )}
              <Icon />
              <span>{label}</span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
