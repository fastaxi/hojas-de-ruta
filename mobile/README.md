# RutasFast Mobile App

App móvil para taxistas en Asturias - Gestión de Hojas de Ruta

## Requisitos

- Node.js 18+
- Expo CLI (`npm install -g expo-cli`)
- Expo Go app en tu dispositivo móvil

## Instalación

```bash
cd mobile
npm install
# o
yarn install
```

## Desarrollo

```bash
# Iniciar servidor de desarrollo
npx expo start

# Opciones de ejecución:
# - Escanea el QR con Expo Go (Android/iOS)
# - Presiona 'a' para Android Emulator
# - Presiona 'i' para iOS Simulator
# - Presiona 'w' para abrir en web
```

## Estructura del Proyecto

```
mobile/
├── App.js                 # Entry point
├── app.json               # Expo configuration
├── package.json           # Dependencies
├── assets/                # Images, icons, splash
└── src/
    ├── contexts/          # React Context providers
    │   └── AuthContext.js    # Autenticación y sesión
    ├── hooks/             # Custom React hooks
    │   ├── index.js
    │   └── usePdfShare.js    # Descarga y compartir PDF
    ├── navigation/        # React Navigation setup
    │   └── Navigation.js
    ├── screens/           # App screens
    │   ├── LoginScreen.js
    │   ├── RegisterScreen.js
    │   ├── HomeScreen.js      # Nueva Hoja de Ruta
    │   ├── HistoryScreen.js   # Histórico + PDF
    │   └── SettingsScreen.js  # Configuración
    ├── services/          # API and utilities
    │   ├── api.js            # Axios + interceptors + token refresh
    │   ├── config.js         # API configuration
    │   └── pdfService.js     # Descarga y compartir PDF
    └── utils/             # Helper functions
        ├── index.js
        └── filename.js       # Sanitización de nombres de archivo
```

## Funcionalidades Implementadas

### Autenticación
- Login con email/contraseña
- Registro en 4 pasos (datos personales, licencia, vehículo, credenciales)
- Refresh token automático (rotación segura)
- Logout con invalidación en servidor
- Almacenamiento seguro de tokens (SecureStore)

### Hojas de Ruta
- Crear nueva hoja de ruta
- Ver histórico con filtros (todas/activas/anuladas)
- Anular hojas (soft delete)

### PDF (MVP)
- **Descargar PDF** individual a almacenamiento local
- **Compartir PDF** vía share sheet nativo (WhatsApp, Email, etc.)
- Manejo de errores:
  - 401: Sesión expirada (auto-refresh o logout)
  - 403: Sin permiso
  - 404: PDF no existe
  - 429: Rate limit (esperar)
- Nombres de archivo seguros (cross-platform)

## API Backend

La app se conecta a: `https://asturia-taxi.emergent.host/api`

### Endpoints Móviles (Auth):
- `POST /auth/mobile/login` - Login → `{ access_token, refresh_token, user }`
- `POST /auth/mobile/refresh` - Renovar token → `{ access_token, refresh_token }`
- `POST /auth/mobile/logout` - Cerrar sesión (invalida refresh token)

### Endpoints de PDF:
- `GET /route-sheets/{id}/pdf` - PDF individual (auth requerida)
- `GET /route-sheets/pdf/range?from_date=...&to_date=...` - PDF por rango

### Flujo de Autenticación:
1. Login → Recibe `access_token` (15 min) + `refresh_token` (30 días)
2. Tokens almacenados en SecureStore (encriptado)
3. Requests incluyen `Authorization: Bearer {access_token}`
4. Si recibe 401 → Auto-refresh con refresh_token
5. Si refresh falla → Logout automático

## Build para Producción

```bash
# Instalar EAS CLI
npm install -g eas-cli

# Login a Expo
eas login

# Configurar proyecto
eas build:configure

# Build para Android (APK/AAB)
eas build --platform android

# Build para iOS
eas build --platform ios

# Build local (requiere Android Studio / Xcode)
npx expo run:android
npx expo run:ios
```

## Configuración EAS

Crear `eas.json`:
```json
{
  "cli": {
    "version": ">= 3.0.0"
  },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal"
    },
    "preview": {
      "distribution": "internal"
    },
    "production": {}
  }
}
```

## Notas Importantes

- Los usuarios deben ser **aprobados por un admin** antes de poder hacer login
- Las hojas de ruta son **inmutables** una vez creadas
- Se pueden **anular** hojas (soft delete con marca de agua en PDF)
- El backend cachea PDFs para mejor rendimiento (headers X-Cache)
- Rate limit de PDF: máximo X requests por minuto (error 429)

## Troubleshooting

### "Sesión expirada" frecuente
- Verifica que el dispositivo tiene hora correcta
- El refresh token dura 30 días, si expira hay que hacer login

### PDF no se comparte
- Verifica permisos de almacenamiento (Android)
- Algunos dispositivos no soportan share sheet

### Error de red
- Verifica conexión a internet
- El backend debe estar accesible desde el dispositivo
