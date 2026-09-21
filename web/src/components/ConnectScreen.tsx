import { useEffect, useState } from "react";
import { probeServer, setServerBase, getServerBase, isAndroidApp } from "../serverConfig";
import { LAN_SERVER_HINT } from "../lanHint";
import { MyoGazeMark } from "../icons";

interface ConnectScreenProps {
  onConnected: () => void;
}

/**
 * First-run pairing for the native app: the phone has to be told where the
 * laptop running the Control App is on the local network.
 */
export function ConnectScreen({ onConnected }: ConnectScreenProps) {
  const [address, setAddress] = useState(
    getServerBase().replace(/^https?:\/\//i, "") || LAN_SERVER_HINT,
  );
  const [status, setStatus] = useState<{ ok: boolean; message: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const saved = getServerBase();
    const candidates = [...new Set(["127.0.0.1:8000", saved, LAN_SERVER_HINT].filter(Boolean))];
    (async () => {
      setBusy(true);
      for (const candidate of candidates) {
        const result = await probeServer(candidate);
        if (cancelled) return;
        if (result.ok) {
          setServerBase(candidate);
          setAddress(candidate.replace(/^https?:\/\//i, ""));
          setStatus(result);
          setBusy(false);
          onConnected();
          return;
        }
      }
      if (!cancelled) {
        setBusy(false);
        setStatus({ ok: false, message: "Laptop not reached yet — same Wi-Fi, then Connect." });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleConnect() {
    setBusy(true);
    setStatus(null);
    const result = await probeServer(address);
    setStatus(result);
    setBusy(false);
    if (result.ok) {
      setServerBase(address);
      onConnected();
    }
  }

  return (
    <div className="connect-screen">
      <div className="connect-card">
        <span className="connect-card__mark" aria-hidden="true">
          <MyoGazeMark size={22} />
        </span>

        <h1>Connect</h1>
        <p className="connect-card__lede">
          {isAndroidApp()
            ? "This phone is the control screen. The laptop webcam watches the lamp. Same Wi-Fi, port 8000."
            : "This phone is the control screen. The laptop webcam watches the lamp. Same Wi-Fi."}
        </p>

        <div className="field">
          <label className="field__label" htmlFor="server-address">
            Server address
          </label>
          <input
            id="server-address"
            className="text-input"
            type="text"
            inputMode="url"
            autoCapitalize="off"
            autoCorrect="off"
            placeholder={LAN_SERVER_HINT}
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void handleConnect();
            }}
          />
          <span className="field__hint">
            {isAndroidApp()
              ? `This laptop is ${LAN_SERVER_HINT}. HTTP only.`
              : `This laptop is ${LAN_SERVER_HINT}.`}
          </span>
        </div>

        {status && (
          <div className="connect-card__status" data-ok={status.ok}>
            {status.message}
          </div>
        )}

        <button type="button" className="btn btn--primary" disabled={busy} onClick={handleConnect}>
          {busy ? "Checking…" : "Connect"}
        </button>
      </div>
    </div>
  );
}
