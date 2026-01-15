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
    │   └── AuthContext.js
    ├── navigation/        # React Navigation setup
    │   └── Navigation.js
    ├── screens/           # App screens
    │   ├── LoginScreen.js
    │   ├── RegisterScreen.js
    │   ├── HomeScreen.js      # Nueva Hoja de Ruta
    │   ├── HistoryScreen.js   # Histórico
    │   └── SettingsScreen.js  # Configuración
    ├── services/          # API and utilities
    │   ├── api.js         # Axios instance + interceptors
    │   └── config.js      # API configuration
    ├── components/        # Reusable components
    ├── hooks/             # Custom hooks
    └── utils/             # Helper functions
```

## API Backend

La app se conecta a: `https://asturia-taxi.emergent.host/api`

### Endpoints Móviles:
- `POST /auth/mobile/login` - Login con JWT
- `POST /auth/mobile/refresh` - Renovar token
- `POST /auth/mobile/logout` - Cerrar sesión

### Flujo de Autenticación:
1. Login → Recibe `access_token` + `refresh_token`
2. Tokens almacenados en SecureStore
3. Auto-refresh cuando expira el access token
4. Logout → Invalida tokens en servidor

## Build para Producción

```bash
# Build para Android (APK/AAB)
eas build --platform android

# Build para iOS
eas build --platform ios

# O usar el build local
npx expo run:android
npx expo run:ios
```

## Configuración EAS (Expo Application Services)

1. Instalar EAS CLI: `npm install -g eas-cli`
2. Login: `eas login`
3. Configurar: `eas build:configure`
4. Build: `eas build --platform all`

## Notas

- Los usuarios deben ser aprobados por un admin antes de poder hacer login
- Las hojas de ruta son inmutables una vez creadas
- Se pueden anular hojas (soft delete con marca de agua en PDF)
