import { useEffect, useRef } from "react";

const ONBOARDED_KEY = "myogaze.onboarded";

export function hasFinishedOnboarding(): boolean {
  return localStorage.getItem(ONBOARDED_KEY) === "1";
}

export function finishOnboarding() {
  localStorage.setItem(ONBOARDED_KEY, "1");
}

interface OnboardingScreenProps {
  onGetStarted: () => void;
  onLogIn: () => void;
}

export function OnboardingScreen({ onGetStarted, onLogIn }: OnboardingScreenProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const cssSize = 320;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.style.width = `${cssSize}px`;
    canvas.style.height = `${cssSize}px`;
    canvas.width = cssSize * dpr;
    canvas.height = cssSize * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const cx = cssSize / 2;
    const cy = cssSize / 2 + 6;
    const radius = 118;
    const count = 900;
    const points = Array.from({ length: count }, (_, i) => {
      const t = i / (count - 1);
      const y = 1 - 2 * t;
      const ring = Math.sqrt(1 - y * y);
      const theta = Math.PI * (1 + Math.sqrt(5)) * i;
      return { x: Math.cos(theta) * ring, y, z: Math.sin(theta) * ring };
    });

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let angle = 0;
    let frame = 0;

    function draw() {
      if (!ctx) return;
      ctx.clearRect(0, 0, cssSize, cssSize);
      const cosA = Math.cos(angle);
      const sinA = Math.sin(angle);
      const tilt = 0.18;
      const cosT = Math.cos(tilt);
      const sinT = Math.sin(tilt);

      for (const p of points) {
        const x1 = p.x * cosA - p.z * sinA;
        const z1 = p.x * sinA + p.z * cosA;
        const y2 = p.y * cosT - z1 * sinT;
        const z2 = p.y * sinT + z1 * cosT;
        if (z2 < -0.15) continue;
        const persp = 260 / (260 + z2 * 90);
        const frontness = (z2 + 1) / 2;
        const rim = Math.max(0, y2 + 0.15);
        const r = 110 + rim * 100;
        const g = 150 + rim * 90;
        ctx.beginPath();
        ctx.fillStyle = `rgba(${r}, ${g}, 255, ${Math.min(0.1 + frontness * 0.35 + rim * 0.35, 0.95)})`;
        ctx.arc(cx + x1 * radius * persp, cy + y2 * radius * persp, 0.7 + frontness * 1.5, 0, Math.PI * 2);
        ctx.fill();
      }

      if (!reduceMotion) {
        angle += 0.0016;
        frame = requestAnimationFrame(draw);
      }
    }

    draw();
    return () => cancelAnimationFrame(frame);
  }, []);

  function start() {
    finishOnboarding();
    onGetStarted();
  }

  function login() {
    finishOnboarding();
    onLogIn();
  }

  return (
    <div className="app-shell mg dark onboard">
      <div className="ob-brand">
        <img src="/mark.svg" alt="MyoGaze" />
      </div>
      <button type="button" className="ob-skip" onClick={login}>
        Skip
      </button>

      <div className="ob-hero">
        <div className="ob-glow" />
        <canvas ref={canvasRef} width={320} height={320} role="img" aria-label="Animated signal visualization" />
      </div>

      <div className="ob-copy">
        <h1>
          Look at the lamp
          <br />
          for two seconds.
        </h1>
        <p>It turns on or off. No tap — just a steady look.</p>
      </div>
      <p className="ob-product">Lamp · two-second look</p>

      <div className="ob-actions">
        <button type="button" className="ob-cta" onClick={start}>
          Get Started
        </button>
        <p className="ob-login">
          Already have an account?{" "}
          <button type="button" onClick={login}>
            Log in
          </button>
        </p>
      </div>
    </div>
  );
}
