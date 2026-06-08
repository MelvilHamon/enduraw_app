import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("regular-42@synth.enduraw");
  const [password, setPassword] = useState("demo1234");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      navigate("/home", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Connexion impossible");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-full max-w-md flex-col justify-center px-6">
      <div className="flex items-center gap-2.5">
        <span className="inline-block h-3 w-3 rounded-full bg-flame-500 shadow-glow" />
        <h1 className="font-display text-3xl uppercase tracking-[0.06em] text-stone-50">Enduraw</h1>
      </div>
      <p className="mt-2 text-sm text-stone-400">
        Connecte-toi avec un athlète seedé (mot de passe&nbsp;: <code className="text-flame-400">demo1234</code>).
      </p>

      <form onSubmit={onSubmit} className="mt-8 flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm text-stone-300">
          Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
            className="rounded-lg border border-ink-600 bg-ink-800 px-3 py-2 text-stone-100 outline-none focus:border-flame-500"
            required
          />
        </label>
        <label className="flex flex-col gap-1 text-sm text-stone-300">
          Mot de passe
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            className="rounded-lg border border-ink-600 bg-ink-800 px-3 py-2 text-stone-100 outline-none focus:border-flame-500"
            required
          />
        </label>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <button
          type="submit"
          disabled={busy}
          className="mt-2 rounded-lg bg-flame-500 px-4 py-3 font-semibold text-ink-950 shadow-glow transition-colors hover:bg-flame-400 disabled:opacity-50"
        >
          {busy ? "Connexion…" : "Se connecter"}
        </button>
      </form>
    </div>
  );
}
