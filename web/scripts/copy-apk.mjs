import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = resolve(webRoot, "..");
const src = join(webRoot, "android", "app", "build", "outputs", "apk", "debug", "app-debug.apk");
const destDir = join(repoRoot, "dist-mobile");
const dest = join(destDir, "MyoGaze.apk");

if (!existsSync(src)) {
  console.error(`APK not found: ${src}`);
  process.exit(1);
}
mkdirSync(destDir, { recursive: true });
copyFileSync(src, dest);
console.log(`Copied ${src} -> ${dest}`);
