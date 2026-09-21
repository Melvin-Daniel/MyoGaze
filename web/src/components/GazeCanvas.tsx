import { useEffect, useRef } from "react";

interface GazeCanvasProps {
  yaw?: number;
  tracking?: boolean;
  compact?: boolean;
  overlay?: boolean;
}

export function GazeCanvas({ yaw = 0, tracking = false, compact = false, overlay = false }: GazeCanvasProps) {
  const ref = useRef<HTMLCanvasElement>(null);
  const yawRef = useRef(yaw);
  const trackingRef = useRef(tracking);
  yawRef.current = yaw;
  trackingRef.current = tracking;

  useEffect(() => {
    const node = ref.current;
    const context = node?.getContext("2d");
    if (!node || !context) return;
    const surface: HTMLCanvasElement = node;
    const gfx: CanvasRenderingContext2D = context;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let dim = { w: 0, h: 0 };
    let t = Math.random() * 10;
    let frame = 0;

    function size() {
      const rect = surface.getBoundingClientRect();
      surface.width = rect.width * dpr;
      surface.height = rect.height * dpr;
      gfx.setTransform(dpr, 0, 0, dpr, 0, 0);
      dim = { w: rect.width, h: rect.height };
    }

    function grid() {
      if (compact || overlay) return;
      gfx.strokeStyle = "rgba(255,255,255,0.05)";
      gfx.lineWidth = 1;
      const step = 24;
      for (let x = 0; x < dim.w; x += step) {
        gfx.beginPath();
        gfx.moveTo(x, 0);
        gfx.lineTo(x, dim.h);
        gfx.stroke();
      }
      for (let y = 0; y < dim.h; y += step) {
        gfx.beginPath();
        gfx.moveTo(0, y);
        gfx.lineTo(dim.w, y);
        gfx.stroke();
      }
    }

    function draw() {
      if (overlay) {
        gfx.clearRect(0, 0, dim.w, dim.h);
      } else {
        gfx.fillStyle = compact ? "rgba(10,12,18,0.18)" : "rgba(10,12,18,0.14)";
        gfx.fillRect(0, 0, dim.w, dim.h);
        if (!compact && t < 0.02) grid();
      }

      let gx = dim.w / 2 + Math.sin(t * 0.6) * dim.w * (compact ? 0.32 : 0.3);
      let gy = dim.h / 2 + Math.cos(t * (compact ? 0.5 : 0.45)) * dim.h * (compact ? 0.3 : 0.28);
      if (!compact) {
        gx += Math.sin(t * 1.7) * dim.w * 0.06;
        gy += Math.cos(t * 1.3) * dim.h * 0.05;
      }
      if (trackingRef.current) {
        gx = dim.w / 2 + Math.max(-1, Math.min(1, yawRef.current)) * dim.w * 0.36;
        gy = dim.h / 2;
      }

      const radius = compact ? 16 : 26;
      const glow = gfx.createRadialGradient(gx, gy, 0, gx, gy, radius);
      glow.addColorStop(0, "rgba(127,166,255,0.9)");
      glow.addColorStop(1, "rgba(127,166,255,0)");
      gfx.fillStyle = glow;
      gfx.beginPath();
      gfx.arc(gx, gy, radius, 0, Math.PI * 2);
      gfx.fill();
      gfx.fillStyle = "#fff";
      gfx.beginPath();
      gfx.arc(gx, gy, compact ? 2.2 : 3.2, 0, Math.PI * 2);
      gfx.fill();

      if (!reduceMotion) {
        t += compact ? 0.01 : 0.012;
        frame = requestAnimationFrame(draw);
      }
    }

    size();
    if (!compact && !overlay) grid();
    draw();
    const onResize = () => {
      size();
      if (!compact && !overlay) grid();
    };
    window.addEventListener("resize", onResize);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", onResize);
    };
  }, [compact, overlay]);

  return <canvas ref={ref} />;
}
