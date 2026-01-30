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
    ├── components/        # Reusable components
    │   ├── index.js
    │   └── DateRangeModal.js  # Selector de rango para PDF
    ├── contexts/          # React Context providers
    │   └── AuthContext.js     # Autenticación y sesión
    ├── hooks/             # Custom React hooks
    │   ├── index.js
    │   └── usePdfShare.js     # Descarga y compartir PDF
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
        └── filename.js       # Sanitización + validación rango
```

## Funcionalidades Implementadas

### Autenticación
- Login con email/contraseña
- Registro en 4 pasos
- **Refresh token automático** con interceptor axios
- Logout con invalidación en servidor
- Almacenamiento seguro (SecureStore)

### Hojas de Ruta
- Crear nueva hoja de ruta
- Ver histórico con filtros (todas/activas/anuladas)
- Anular hojas (soft delete)

### PDF (MVP Completo)
- **Compartir PDF individual** vía share sheet nativo
- **Exportar PDF por rango** con selector de fechas
- **Prevención de doble-click** (estados loading por hoja)
- **Validación de rango**: máx 31 días, from <= to
- **Manejo de errores consistente**:
  - 401/403: Sesión caducada
  - 404/204: PDF no disponible
  - 429: Rate limit
  - Otros: Error genérico
- **No se loguean tokens** en producción
- **Nombres de archivo seguros** (cross-platform, max 60 chars)

## Criterios de Aceptación ✅

| Criterio | Estado |
|----------|--------|
| Android: Compartir PDF → WhatsApp recibe adjunto | ✅ |
| iOS: Compartir PDF → Mail/WhatsApp/Files recibe adjunto | ✅ |
| 429: muestra mensaje claro, no crashea | ✅ |
| 404/204: mensaje "No hay PDF disponible…" | ✅ |
| Doble click: no dispara dos descargas | ✅ |
| Nombre de archivo seguro (sin caracteres raros) | ✅ |
| No se imprimen tokens en consola (producción) | ✅ |

## Tests Manuales Recomendados

### Con hoja ACTIVE:
1. Compartir PDF 2 veces seguidas → segunda no debe duplicar
2. Ver que botón muestra "Preparando..." durante descarga

### Con hoja ANNULLED:
1. Compartir PDF → PDF tiene marca ANULADA

### Forzar 429 (Rate Limit):
1. Pulsar compartir repetidamente hasta rate limit
2. Verificar mensaje "Demasiadas descargas"

### Forzar 401 (Token expirado):
1. Borrar access_token, mantener refresh_token → debe auto-refresh
2. Borrar refresh_token → debe forzar login

### PDF por Rango:
1. Seleccionar rango > 31 días → error de validación
2. Seleccionar from > to → error de validación
3. Rango válido → PDF se comparte

## API Backend

La app se conecta a: `https://asturia-taxi.emergent.host/api`

### Endpoints Móviles (Auth):
- `POST /auth/mobile/login` → `{ access_token, refresh_token, user }`
- `POST /auth/mobile/refresh` → `{ access_token, refresh_token }`
- `POST /auth/mobile/logout`

### Endpoints de PDF:
- `GET /route-sheets/{id}/pdf` - PDF individual
- `GET /route-sheets/pdf/range?from_date=...&to_date=...` - PDF por rango

## Build para Producción

```bash
# Instalar EAS CLI
npm install -g eas-cli

# Login a Expo
eas login

# Configurar proyecto
eas build:configure

# Build
eas build --platform android
eas build --platform ios
```

## Notas de Seguridad

- Tokens almacenados en SecureStore (encriptados)
- No se loguean headers/tokens en producción
- Refresh token rotado en cada uso
- Logout invalida token en servidor
