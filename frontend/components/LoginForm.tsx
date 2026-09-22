"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, login } from "@/lib/api";
import { DEMO_ACCOUNTS, roleStyle } from "@/lib/roles";

export function LoginForm() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(user: string, pass: string) {
    setBusy(true);
    setError(null);
    try {
      await login(user, pass);
      router.push("/chat");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed");
      setBusy(false);
    }
  }

  return (
    <div className="w-full max-w-md">
      <div className="mb-6 text-center">
        <div className="mb-3 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-900 text-xl font-bold text-white">
          M
        </div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">MediBot</h1>
        <p className="mt-1 text-sm text-slate-500">MediAssist Health Network · internal assistant</p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void submit(username, password);
        }}
        className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
      >
        <label className="block text-xs font-medium text-slate-600">Username</label>
        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10"
          placeholder="nurse.priya"
        />

        <label className="mt-3 block text-xs font-medium text-slate-600">Password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900 focus:ring-2 focus:ring-slate-900/10"
          placeholder="••••••"
        />

        {error && (
          <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">{error}</p>
        )}

        <button
          type="submit"
          disabled={busy || !username || !password}
          className="mt-4 w-full rounded-lg bg-slate-900 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>

      {/* One click per role. A reviewer who can switch roles instantly will
          exercise the access control far more than one who has to type. */}
      <div className="mt-5">
        <p className="mb-2 text-center text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Demo accounts — click to sign in
        </p>
        <div className="space-y-1.5">
          {DEMO_ACCOUNTS.map((account) => {
            const style = roleStyle(account.role);
            return (
              <button
                key={account.username}
                disabled={busy}
                onClick={() => {
                  setUsername(account.username);
                  setPassword(account.password);
                  void submit(account.username, account.password);
                }}
                className="flex w-full items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-left transition hover:border-slate-400 hover:shadow-sm disabled:opacity-50"
              >
                <span className={`h-2 w-2 flex-none rounded-full ${style.dot}`} />
                <span className="flex-1 min-w-0">
                  <span className="block font-mono text-xs font-medium text-slate-800">
                    {account.username}
                  </span>
                  <span className="block truncate text-[11px] text-slate-500">
                    {account.blurb}
                  </span>
                </span>
                <span
                  className={`flex-none rounded-full px-2 py-0.5 text-[10px] font-semibold ring-1 ring-inset ${style.chip}`}
                >
                  {style.label}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
