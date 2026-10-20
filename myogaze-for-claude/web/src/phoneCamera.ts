/** Capture JPEG frames from this device's camera and hand them to the laptop. */

export type PhoneCameraError = {
  code: "insecure" | "denied" | "missing" | "failed";
  message: string;
};

function describe(err: unknown): PhoneCameraError {
  if (!window.isSecureContext) {
    return {
      code: "insecure",
      message:
        "iPhone Safari blocks the camera on HTTP. Open the HTTPS address (port 8443) shown on the laptop, tap through the certificate warning, then Start session.",
    };
  }
  const name = err && typeof err === "object" && "name" in err ? String((err as { name: string }).name) : "";
  if (name === "NotAllowedError" || name === "PermissionDeniedError") {
    return { code: "denied", message: "Camera permission denied. Allow the camera and tap Start again." };
  }
  if (name === "NotFoundError" || name === "DevicesNotFoundError") {
    return { code: "missing", message: "No camera found on this device." };
  }
  const msg = err instanceof Error ? err.message : String(err);
  return { code: "failed", message: msg || "Could not start this device's camera." };
}

function fail(err: unknown): never {
  const info = describe(err);
  const error = new Error(info.message);
  error.name = info.code;
  throw error;
}

async function openBackCamera(): Promise<MediaStream> {
  const attempts: MediaStreamConstraints[] = [
    { audio: false, video: { facingMode: { exact: "environment" }, width: { ideal: 640 }, height: { ideal: 480 } } },
    { audio: false, video: { facingMode: { ideal: "environment" }, width: { ideal: 640 }, height: { ideal: 480 } } },
    { audio: false, video: { facingMode: "environment" } },
  ];
  let last: unknown;
  for (const constraints of attempts) {
    try {
      return await navigator.mediaDevices.getUserMedia(constraints);
    } catch (err) {
      last = err;
    }
  }
  fail(last);
}

class PhoneCamera {
  private stream: MediaStream | null = null;
  private timer: number | null = null;
  private video: HTMLVideoElement | null = null;
  private canvas: HTMLCanvasElement | null = null;
  private onFrame: ((jpegB64: string) => void) | null = null;
  private pumping = false;
  private lastSent = 0;

  get active(): boolean {
    return this.stream != null;
  }

  async start(onFrame: (jpegB64: string) => void): Promise<void> {
    if (!navigator.mediaDevices?.getUserMedia) {
      fail({ name: "NotFoundError" });
    }
    if (!window.isSecureContext) {
      fail({ name: "SecurityError" });
    }
    this.stop();
    this.onFrame = onFrame;
    try {
      const stream = await openBackCamera();
      this.stream = stream;
      const video = document.createElement("video");
      video.setAttribute("playsinline", "true");
      video.setAttribute("webkit-playsinline", "true");
      video.playsInline = true;
      video.muted = true;
      video.autoplay = true;
      video.srcObject = stream;
      video.style.position = "fixed";
      video.style.opacity = "0";
      video.style.pointerEvents = "none";
      video.style.width = "1px";
      video.style.height = "1px";
      video.style.bottom = "0";
      video.style.left = "0";
      document.body.appendChild(video);
      this.video = video;
      await video.play();
      this.canvas = document.createElement("canvas");
      this.pumping = true;
      const loop = () => {
        if (!this.pumping) return;
        this.capture();
        this.timer = window.setTimeout(loop, 180);
      };
      loop();
    } catch (err) {
      this.stop();
      fail(err);
    }
  }

  stop(): void {
    this.pumping = false;
    if (this.timer != null) {
      window.clearTimeout(this.timer);
      this.timer = null;
    }
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    this.onFrame = null;
    if (this.video) {
      this.video.srcObject = null;
      this.video.remove();
      this.video = null;
    }
    this.canvas = null;
  }

  private capture(): void {
    const video = this.video;
    const canvas = this.canvas;
    const onFrame = this.onFrame;
    if (!video || !canvas || !onFrame) return;
    if (video.readyState < 2) return;
    const now = performance.now();
    if (now - this.lastSent < 160) return;
    const vw = video.videoWidth || 640;
    const vh = video.videoHeight || 480;
    const scale = Math.min(1, 480 / vw);
    const w = Math.max(160, Math.round(vw * scale));
    const h = Math.max(120, Math.round(vh * scale));
    if (canvas.width !== w) canvas.width = w;
    if (canvas.height !== h) canvas.height = h;
    const ctx = canvas.getContext("2d", { alpha: false });
    if (!ctx) return;
    ctx.drawImage(video, 0, 0, w, h);
    const data = canvas.toDataURL("image/jpeg", 0.4);
    const comma = data.indexOf(",");
    if (comma < 0) return;
    this.lastSent = now;
    onFrame(data.slice(comma + 1));
  }
}

export const phoneCamera = new PhoneCamera();
