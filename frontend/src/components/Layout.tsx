import type { ReactNode } from "react";
import { useAuth } from "../auth/AuthContext";
import { BottomNav } from "./BottomNav";

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  return (
    <div className="mx-auto flex min-h-full max-w-md flex-col">
      <header className="flex items-center justify-between px-4 py-3">
        <span className="text-sm font-semibold tracking-tight text-slate-200">Enduraw</span>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          {user && <span className="max-w-[160px] truncate">{user.persona_id ?? user.email}</span>}
          <button type="button" onClick={logout} className="text-slate-400 underline">
            Quitter
          </button>
        </div>
      </header>
      <main className="flex-1 px-4 pb-4">{children}</main>
      <BottomNav />
    </div>
  );
}
