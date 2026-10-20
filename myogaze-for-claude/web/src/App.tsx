import { useEffect, useRef, useState } from "react";
import { useNeuroShift } from "./useNeuroShift";
import { needsServerSetup } from "./serverConfig";
import { currentUser, signOut, type AccountUser } from "./auth";
import { ConnectScreen } from "./components/ConnectScreen";
import { AuthScreen } from "./components/AuthScreen";
import { hasFinishedOnboarding, OnboardingScreen } from "./components/OnboardingScreen";
import { TabBar } from "./components/Nav";
import { ToastStack } from "./components/Toast";
import { HomeView } from "./components/views/HomeView";
import { LiveView } from "./components/views/LiveView";
import { ActivityView } from "./components/views/ActivityView";
import { SettingsView } from "./components/views/SettingsView";
import type { ActivityChip } from "./activityLog";
import { PrefsProvider, isQuietHour, usePrefs } from "./settings/prefs";
import type { ToastMessage } from "./types";

export type TabId = "home" | "live" | "activity" | "settings";
export type NestedId = "live" | "history" | "insights";

export default function App() {
  const [paired, setPaired] = useState(!needsServerSetup());
  const [user, setUser] = useState<AccountUser | null>(null);
  const [authReady, setAuthReady] = useState(false);
  const [onboarded, setOnboarded] = useState(hasFinishedOnboarding);
  const [authMode, setAuthMode] = useState<"create" | "signin">("create");

  useEffect(() => {
    if (!paired) return;
    currentUser()
      .then(setUser)
      .finally(() => setAuthReady(true));
  }, [paired]);

  if (!paired) {
    return <ConnectScreen onConnected={() => setPaired(true)} />;
  }
  if (!authReady) {
    return <div className="app-shell" />;
  }
  if (!user && !onboarded) {
    return (
      <OnboardingScreen
        onGetStarted={() => {
          setAuthMode("create");
          setOnboarded(true);
        }}
        onLogIn={() => {
          setAuthMode("signin");
          setOnboarded(true);
        }}
      />
    );
  }
  if (!user) {
    return <AuthScreen onSignedIn={setUser} initialMode={authMode} />;
  }

  return (
    <PrefsProvider>
      <Shell user={user} onSignOut={() => signOut().then(() => setUser(null))} />
    </PrefsProvider>
  );
}

const TRACK_MS = "myogaze-track-ms";
const TRACK_DAY = "myogaze-track-day";

function firstName(name: string): string {
  const raw = name.trim().split(/\s+/)[0] || "there";
  return raw.charAt(0).toUpperCase() + raw.slice(1);
}

function loadTrackedMs(): number {
  const day = new Date().toDateString();
  try {
    if (localStorage.getItem(TRACK_DAY) !== day) {
      localStorage.setItem(TRACK_DAY, day);
      localStorage.setItem(TRACK_MS, "0");
      return 0;
    }
    return Number(localStorage.getItem(TRACK_MS) || 0) || 0;
  } catch {
    return 0;
  }
}

function saveTrackedMs(ms: number) {
  try {
    localStorage.setItem(TRACK_DAY, new Date().toDateString());
    localStorage.setItem(TRACK_MS, String(ms));
  } catch {
    /* private mode */
  }
}

function Shell({ user, onSignOut }: { user: AccountUser; onSignOut: () => void }) {
  const engine = useNeuroShift();
  const { prefs } = usePrefs();
  const [tab, setTab] = useState<TabId>("home");
  const [paused, setPaused] = useState(false);
  const [activityChip, setActivityChip] = useState<ActivityChip>("all");
  const [trackedMs, setTrackedMs] = useState(loadTrackedMs);
  const [localToasts, setLocalToasts] = useState<ToastMessage[]>([]);
  const running = engine.sessionState === "running";
  const lastAct = useRef("");
  const lastLink = useRef(engine.connection);

  function pushLocal(text: string, tone: ToastMessage["tone"] = "neutral") {
    const toast: ToastMessage = { id: `${Date.now()}-${Math.random()}`, text, tone };
    setLocalToasts((prev) => [...prev, toast].slice(-3));
    window.setTimeout(() => setLocalToasts((prev) => prev.filter((item) => item.id !== toast.id)), 4000);
  }

  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => {
      setTrackedMs((prev) => {
        const next = prev + 1000;
        saveTrackedMs(next);
        return next;
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [running]);

  useEffect(() => {
    const start = new Date();
    start.setHours(0, 0, 0, 0);
    const stamps = engine.activity.map((item) => item.timestamp).filter((ts) => ts >= start.getTime());
    if (!stamps.length) return;
    const oldest = Math.min(...stamps);
    const span = (running ? Date.now() : Math.max(...stamps)) - oldest;
    setTrackedMs((prev) => {
      if (prev >= span) return prev;
      saveTrackedMs(span);
      return span;
    });
  }, [engine.activity, running]);

  useEffect(() => {
    if (engine.connection === "offline" && lastLink.current !== "offline" && prefs.notifications.laptopDisconnected) {
      pushLocal("Laptop disconnected", "abstain");
    }
    lastLink.current = engine.connection;
  }, [engine.connection, prefs.notifications.laptopDisconnected]);

  useEffect(() => {
    if (!prefs.accessibility.audioFeedback) return;
    if (engine.decision.action !== "ACT" || !engine.decision.selected_label) return;
    const key = `${engine.decision.selected_label}-${engine.stats.actuations}`;
    if (lastAct.current === key) return;
    lastAct.current = key;
    try {
      const ctx = new AudioContext();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = 880;
      gain.gain.value = 0.06;
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.08);
    } catch {
      /* autoplay blocked */
    }
  }, [engine.decision, engine.stats.actuations, prefs.accessibility.audioFeedback]);

  useEffect(() => {
    if (!prefs.breaks.enabled || !prefs.notifications.breakReminders) return;
    const ms = prefs.breaks.intervalMin * 60_000;
    const timer = window.setInterval(() => {
      if (isQuietHour(new Date(), prefs)) return;
      pushLocal("Time for an eye break — look away from the screen for a moment.", "neutral");
    }, ms);
    return () => window.clearInterval(timer);
  }, [prefs]);

  useEffect(() => {
    if (!prefs.notifications.dailySummary) return;
    const day = new Date().toDateString();
    const key = "myogaze.daily-summary-day";
    try {
      if (localStorage.getItem(key) === day) return;
      localStorage.setItem(key, day);
    } catch {
      return;
    }
    const minutes = Math.floor(loadTrackedMs() / 60000);
    pushLocal(minutes ? `Today: ${minutes}m in session` : "No session yet today", "neutral");
  }, [prefs.notifications.dailySummary]);

  function openLive(force = false) {
    if (force || (engine.sessionState === "idle" && !paused)) {
      void engine.startSession();
      setPaused(false);
    }
    setTab("live");
  }

  function goTab(next: TabId) {
    if (next === "live") {
      openLive(false);
      return;
    }
    if (next === "activity") setActivityChip("all");
    setTab(next);
  }

  const visibleToasts = [...engine.toasts, ...localToasts].filter((toast) => {
    if (!prefs.notifications.calibration && /calibrat/i.test(toast.text)) return false;
    return true;
  });

  return (
    <div
      className="app-shell rd"
      data-text={prefs.accessibility.textSize}
      data-contrast={prefs.accessibility.highContrast ? "high" : "off"}
      data-motion={prefs.accessibility.reduceMotion ? "reduce" : "ok"}
    >
      {tab === "home" && (
        <HomeView
          engine={engine}
          account={user}
          trackedMs={trackedMs}
          onOpenLive={() => openLive(true)}
          onOpenReview={() => {
            setActivityChip("review");
            setTab("activity");
          }}
          onOpenActivity={() => {
            setActivityChip("all");
            setTab("activity");
          }}
          onOpenSettings={() => setTab("settings")}
        />
      )}
      {tab === "live" && (
        <LiveView
          engine={engine}
          personName={firstName(user.name)}
          onBack={() => setTab("home")}
          onOpenSettings={() => setTab("settings")}
          onPaused={setPaused}
        />
      )}
      {tab === "activity" && (
        <ActivityView engine={engine} personName={firstName(user.name)} initialChip={activityChip} />
      )}
      {tab === "settings" && (
        <SettingsView engine={engine} account={user} onSignOut={onSignOut} onOpenLive={() => openLive(true)} />
      )}
      <TabBar active={tab} onNavigate={goTab} />
      <ToastStack toasts={visibleToasts} />
    </div>
  );
}
