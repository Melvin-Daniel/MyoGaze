import { useState, type FormEvent } from "react";
import { HomeIcon } from "../icons";
import { signIn, signUp, type AccountUser } from "../auth";

interface AuthScreenProps {
  onSignedIn: (user: AccountUser) => void;
  initialMode?: "create" | "signin";
}

export function AuthScreen({ onSignedIn, initialMode = "create" }: AuthScreenProps) {
  const [mode, setMode] = useState<"create" | "signin">(initialMode);
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (mode === "create" && password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      const user =
        mode === "create" ? await signUp(identifier, password) : await signIn(identifier, password);
      onSignedIn(user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not continue.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app-shell auth-screen">
      <form className="auth-card" onSubmit={submit}>
        <div className="auth-brand">
          <HomeIcon size={18} />
          <span>MyoGaze</span>
        </div>
        <h1>{mode === "create" ? "Create account" : "Welcome back"}</h1>
        <p className="auth-lead">
          {mode === "create"
            ? "One account on this laptop. Then look at the lamp for two seconds to toggle it."
            : "Sign in to this laptop. Gaze does the rest."}
        </p>

        <label className="auth-field">
          <span>Email or phone</span>
          <input
            autoComplete="username"
            inputMode="email"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            placeholder="name@email.com"
          />
        </label>
        <label className="auth-field">
          <span>Password</span>
          <input
            type="password"
            autoComplete={mode === "create" ? "new-password" : "current-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 8 characters"
          />
        </label>
        {mode === "create" && (
          <label className="auth-field">
            <span>Confirm password</span>
            <input
              type="password"
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
          </label>
        )}

        {error && <p className="auth-error">{error}</p>}

        <button type="submit" className="auth-submit" disabled={busy}>
          {busy ? "Please wait" : mode === "create" ? "Create account" : "Sign in"}
        </button>
        <button
          type="button"
          className="auth-switch"
          onClick={() => {
            setMode(mode === "create" ? "signin" : "create");
            setError("");
          }}
        >
          {mode === "create" ? "Already have an account? Sign in" : "New here? Create account"}
        </button>
      </form>
    </div>
  );
}
