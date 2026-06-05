import { NavLink } from "react-router-dom";

const ITEMS = [
  { to: "/today", label: "Aujourd'hui", icon: "📊" },
  { to: "/checkin", label: "Check-in", icon: "✓" },
  { to: "/body", label: "Corps", icon: "🦵" },
  { to: "/tests", label: "Tests", icon: "⚡" },
  { to: "/insights", label: "Courbes", icon: "📈" },
];

export function BottomNav() {
  return (
    <nav className="sticky bottom-0 z-10 grid grid-cols-5 border-t border-slate-800 bg-slate-950/95 pb-[env(safe-area-inset-bottom)] backdrop-blur">
      {ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            `flex flex-col items-center gap-0.5 py-2 text-[11px] ${
              isActive ? "text-slate-100" : "text-slate-500"
            }`
          }
        >
          <span className="text-lg leading-none">{item.icon}</span>
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}
