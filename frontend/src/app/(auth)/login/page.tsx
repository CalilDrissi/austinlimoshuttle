"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { authService } from "@/lib/api/auth.service";
import { useRefreshAuth } from "@/hooks/useAuth";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const refreshAuth = useRefreshAuth();
  const next = params.get("next") || "/account";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await authService.login({ email: email.trim(), password });
      await refreshAuth();
      router.push(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed.");
      setBusy(false);
    }
  };

  return (
    <section className="section pt-80 pb-80">
      <div className="container" style={{ maxWidth: 440 }}>
        <h2 className="heading-36-medium mb-10">Sign in</h2>
        <p className="text-14 color-grey mb-30">
          New here? <Link href={`/register?next=${encodeURIComponent(next)}`}>Create an account</Link>
        </p>
        <form onSubmit={submit}>
          <div className="mb-20">
            <label className="text-14 color-grey">Email</label>
            <input type="email" className="form-control" required value={email}
              onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="mb-10">
            <label className="text-14 color-grey">Password</label>
            <input type="password" className="form-control" required value={password}
              onChange={(e) => setPassword(e.target.value)} />
          </div>
          <p className="text-13 mb-20"><Link href="/reset-password">Forgot password?</Link></p>
          {error && <p className="text-14 mb-15" style={{ color: "#c0392b" }}>{error}</p>}
          <button className="btn btn-primary hover-up w-100" type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>

        {next.startsWith("/booking") && (
          <>
            <div className="text-14 color-grey" style={{ textAlign: "center", margin: "18px 0" }}>— or —</div>
            <button className="btn btn-white hover-up w-100" type="button" onClick={() => router.push(next)}>
              Continue as guest
            </button>
            <p className="text-13 color-grey mt-10" style={{ textAlign: "center" }}>
              No account needed — you&apos;ll get a receipt by email.
            </p>
          </>
        )}
      </div>
    </section>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
