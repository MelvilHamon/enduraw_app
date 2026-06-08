import type { ReactNode } from "react";
import { useAuth } from "../auth/AuthContext";
import { BottomNav } from "./BottomNav";

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  return (
    <div className="mx-auto flex min-h-full max-w-md flex-col">
      <header className="flex items-center justify-between px-4 py-3">
        <span className="flex items-center gap-2">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-flame-500 shadow-glow" />
          <span className="font-display text-lg uppercase tracking-[0.08em] text-stone-50">Enduraw</span>
        </span>
        <div className="flex items-center gap-3 text-xs text-stone-400">
          {user && (
            <span className="max-w-[160px] truncate">{user.persona_id ?? user.email}</span>
          )}
          <button
            type="button"
            onClick={logout}
            className="rounded text-stone-400 underline-offset-2 hover:text-flame-500 hover:underline"
          >
            Quitter
          </button>
        </div>
      </header>
      <main className="flex-1 px-4 pb-4">{children}</main>
      <BottomNav />
    </div>
  );
}
