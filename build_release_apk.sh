#!/usr/bin/env bash
set -euo pipefail

# ====== Config ======
APP_NAME="RutasFast"
MOBILE_DIR="mobile"
KEYSTORE_PATH="$HOME/keystores/rutasfast-release.p12"
KEY_ALIAS="rutasfast"

KC_STORE_SERVICE="rutasfast_store_pass"
KC_KEY_SERVICE="rutasfast_key_pass"

# ====== Helpers ======
die(){ echo "ERROR: $*" >&2; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "No encuentro el comando: $1"
}

get_keychain() {
  local service="$1"
  security find-generic-password -a "$USER" -s "$service" -w 2>/dev/null || true
}

set_keychain() {
  local service="$1"
  local secret="$2"
  security add-generic-password -a "$USER" -s "$service" -w "$secret" -U >/dev/null
}

# ====== Preconditions ======
need_cmd node
need_cmd npm
need_cmd python3
need_cmd security

# Cargar nvm si existe (para usar Node 18)
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
  # shellcheck disable=SC1090
  . "$NVM_DIR/nvm.sh"
  if command -v nvm >/dev/null 2>&1; then
    nvm use 18 >/dev/null || true
  fi
fi

[ -f "$KEYSTORE_PATH" ] || die "No existe el keystore: $KEYSTORE_PATH"
chmod 600 "$KEYSTORE_PATH" 2>/dev/null || true

# ====== Secrets from Keychain (or prompt) ======
STORE_PASS="$(get_keychain "$KC_STORE_SERVICE")"
if [ -z "$STORE_PASS" ]; then
  read -r -s -p "Password del keystore (STORE): " STORE_PASS; echo
  [ -n "$STORE_PASS" ] || die "STORE password vacía"
  set_keychain "$KC_STORE_SERVICE" "$STORE_PASS"
  echo "OK: STORE guardada en Keychain ($KC_STORE_SERVICE)"
fi

KEY_PASS="$(get_keychain "$KC_KEY_SERVICE")"
if [ -z "$KEY_PASS" ]; then
  read -r -s -p "Password de la clave (KEY) (Enter = misma que STORE): " KEY_PASS; echo
  if [ -z "$KEY_PASS" ]; then KEY_PASS="$STORE_PASS"; fi
  set_keychain "$KC_KEY_SERVICE" "$KEY_PASS"
  echo "OK: KEY guardada en Keychain ($KC_KEY_SERVICE)"
fi

export RUTASFAST_UPLOAD_STORE_PASSWORD="$STORE_PASS"
export RUTASFAST_UPLOAD_KEY_PASSWORD="$KEY_PASS"

# ====== Build ======
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR/$MOBILE_DIR"

echo "==> npm ci"
rm -rf node_modules
npm ci --no-audit --no-fund

echo "==> expo prebuild (android) --clean"
rm -rf android
npx expo prebuild --platform android --clean

cd android

echo "==> Escribiendo gradle.properties (sin passwords)"
python3 - <<PY
from pathlib import Path
p = Path("gradle.properties")
lines = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
wanted = {
  "RUTASFAST_UPLOAD_STORE_FILE": "$KEYSTORE_PATH",
  "RUTASFAST_UPLOAD_KEY_ALIAS": "$KEY_ALIAS",
}
out = []
seen = set()
for line in lines:
    if "=" in line and not line.lstrip().startswith("#"):
        k, v = line.split("=", 1)
        k = k.strip()
        if k in wanted:
            out.append(f"{k}={wanted[k]}")
            seen.add(k)
            continue
    out.append(line)
for k, v in wanted.items():
    if k not in seen:
        out.append(f"{k}={v}")
p.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
print("OK: gradle.properties actualizado.")
PY

echo "==> Parcheando app/build.gradle (release firma por ENV)"
python3 - <<'PY'
from pathlib import Path
import re

p = Path("app/build.gradle")
s = p.read_text(encoding="utf-8")

def find_block(src, name):
    m = re.search(rf"(^[ \t]*){re.escape(name)}\s*\{{", src, flags=re.M)
    if not m:
        return None
    indent = m.group(1)
    start = m.start()
    brace = src.find("{", m.end()-1)
    depth = 0
    end = None
    for i in range(brace, len(src)):
        if src[i] == "{": depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    return start, end, indent

signing_block = """    signingConfigs {
        debug {
            storeFile file('debug.keystore')
            storePassword 'android'
            keyAlias 'androiddebugkey'
            keyPassword 'android'
        }
        release {
            if (project.hasProperty('RUTASFAST_UPLOAD_STORE_FILE') && project.hasProperty('RUTASFAST_UPLOAD_KEY_ALIAS')) {
                def sp = System.getenv("RUTASFAST_UPLOAD_STORE_PASSWORD")
                def kp = System.getenv("RUTASFAST_UPLOAD_KEY_PASSWORD") ?: sp
                if (!sp || !kp) {
                    throw new GradleException("Missing signing env vars for RELEASE. Set RUTASFAST_UPLOAD_STORE_PASSWORD and RUTASFAST_UPLOAD_KEY_PASSWORD.")
                }
                storeFile file(RUTASFAST_UPLOAD_STORE_FILE)
                storePassword sp
                keyAlias RUTASFAST_UPLOAD_KEY_ALIAS
                keyPassword kp
            } else {
                throw new GradleException("Missing signing properties for RELEASE. Set RUTASFAST_UPLOAD_STORE_FILE and RUTASFAST_UPLOAD_KEY_ALIAS in android/gradle.properties")
            }
        }
    }
"""

blk = find_block(s, "signingConfigs")
if not blk:
    raise SystemExit("ERROR: No encuentro signingConfigs { } en app/build.gradle")
start, end, indent = blk
s = s[:start] + signing_block + s[end:]  # bloque completo

# Forzar buildTypes.release => signingConfigs.release
# (sin tocar debug)
s = re.sub(
    r"(buildTypes\s*\{.*?release\s*\{.*?\n\s*)signingConfig\s+signingConfigs\.\w+",
    r"\1signingConfig signingConfigs.release",
    s,
    flags=re.S
)

p.write_text(s, encoding="utf-8")
print("OK: build.gradle parcheado.")
PY

echo "==> Gradle assembleRelease"
./gradlew --stop >/dev/null 2>&1 || true
./gradlew clean assembleRelease --no-daemon

APK_PATH="app/build/outputs/apk/release/app-release.apk"
[ -f "$APK_PATH" ] || die "No encuentro el APK: $APK_PATH"

OUT_APK="$HOME/Desktop/${APP_NAME}-release-$(date +%Y%m%d-%H%M).apk"
cp "$APK_PATH" "$OUT_APK"

echo "==> APK generado: $OUT_APK"
echo "==> SHA256:"
shasum -a 256 "$OUT_APK"

# apksigner (si existe)
SDK="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-$HOME/Library/Android/sdk}}"
APKSIGNER="$(ls "$SDK"/build-tools/*/apksigner 2>/dev/null | sort -V | tail -n 1 || true)"
if [ -n "$APKSIGNER" ]; then
  echo "==> Certificado (apksigner):"
  "$APKSIGNER" verify --print-certs "$OUT_APK" | sed -n '1,60p'
else
  echo "INFO: apksigner no encontrado (saltando verify)."
fi
