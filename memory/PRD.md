# RutasFast - PRD (Product Requirements Document)

## Estado Actual
**Fecha última actualización**: 2026-01-09
**Fase**: MVP Completo con Sistema de Autenticación Seguro

## Descripción del Proyecto
App para taxistas en Asturias que permite generar "Hojas de Ruta" numeradas, conservar histórico, exportar a PDF y compartir por email. Incluye panel web de administración para validar usuarios.

## Stack Tecnológico
- **Frontend**: React Web (PWA responsive)
- **Backend**: FastAPI (Python)
- **Base de Datos**: MongoDB
- **Email**: Deshabilitado (sistema de reset manual por admin)
- **PDF**: ReportLab
- **Autenticación**: httpOnly cookies (refresh token) + JWT en memoria (access token)

## Arquitectura

### Colecciones MongoDB
1. **users** - Usuarios taxistas
   - Índice único: `email`
   - Campos: id, full_name, dni_cif, license_number, license_council, phone, email, password_hash, status (PENDING|APPROVED), vehicle_*, token_version, must_change_password, temp_password_expires_at, created_at, updated_at

2. **drivers** - Choferes de usuarios
   - Índice: `user_id`
   - Campos: id, user_id, full_name, dni, created_at

3. **route_sheets** - Hojas de ruta
   - Índices: user_id+created_at, user_id+year+seq_number, status, user_visible
   - Campos: id, user_id, year, seq_number, conductor_driver_id, contractor_*, prebooked_*, pickup_*, destination, status (ACTIVE|ANNULLED), annulled_at, annul_reason, user_visible, hide_at, purge_at, created_at

4. **app_config** - Configuración global (documento único id="global")
   - Campos: header_title, header_line1, header_line2, legend_text, hide_after_months, purge_after_months

5. **counters** - Contadores atómicos para numeración
   - Índice: user_id+year (unique)
   - Campos: user_id, year, seq

6. **admin_audit_logs** - Registro de acciones administrativas
   - Campos: action, admin_username, user_id, user_email, timestamp

### Rutas Frontend
- `/` - Landing page
- `/app/login` - Login usuario
- `/app/registro` - Registro multi-step (4 pasos)
- `/app/cambiar-password` - Página forzada para cambiar contraseña temporal
- `/app/nueva-hoja` - Crear hoja de ruta
- `/app/historico` - Ver histórico + filtros + anular + PDF
- `/app/configuracion` - Editar perfil/vehículo/choferes (3 tabs)
- `/admin/login` - Login admin
- `/admin/usuarios` - Gestión usuarios + aprobación + reset contraseña
- `/admin/hojas` - Ver todas las hojas
- `/admin/config` - Configuración global + ejecutar retención manual

### Endpoints API (/api)

#### Auth
- POST `/auth/register` - Registro usuario
- POST `/auth/login` - Login usuario (devuelve access_token + cookie refresh)
- POST `/auth/refresh` - Renovar tokens (usa cookie httpOnly)
- POST `/auth/logout` - Cerrar sesión (limpia cookies)
- POST `/auth/forgot-password` - ⚠️ DESHABILITADO (410 Gone)
- POST `/auth/reset-password` - ⚠️ DESHABILITADO (410 Gone)

#### User (requiere auth)
- GET `/me` - Obtener perfil
- PUT `/me` - Actualizar perfil
- POST `/me/change-password` - Cambiar contraseña (logged in)
- GET `/me/drivers` - Listar choferes
- POST `/me/drivers` - Añadir chofer
- PUT `/me/drivers/{id}` - Editar chofer
- DELETE `/me/drivers/{id}` - Eliminar chofer

#### Route Sheets (requiere auth)
- POST `/route-sheets` - Crear hoja
- GET `/route-sheets` - Listar hojas (con filtros)
- GET `/route-sheets/{id}` - Ver hoja
- POST `/route-sheets/{id}/annul` - Anular hoja
- GET `/route-sheets/{id}/pdf` - Descargar PDF individual
- GET `/route-sheets/pdf/range` - Descargar PDF por rango

#### Admin
- POST `/admin/login` - Login admin
- GET `/admin/users` - Listar usuarios
- GET `/admin/users/{id}` - Ver usuario
- PUT `/admin/users/{id}` - Editar usuario
- POST `/admin/users/{id}/approve` - Aprobar usuario
- POST `/admin/users/{id}/reset-password-temp` - Generar contraseña temporal (72h)
- GET `/admin/route-sheets` - Listar todas las hojas
- GET `/admin/config` - Ver config
- PUT `/admin/config` - Actualizar config
- POST `/admin/run-retention` - Ejecutar job de retención manualmente
- GET `/admin/retention-runs` - Historial de ejecuciones de retención
- GET `/admin/retention-runs/last` - Última ejecución de retención

#### Internal (para schedulers)
- POST `/internal/run-retention` - Ejecutar retención (requiere header X-Job-Token)

## Lo Implementado ✅
1. ✅ Modelo de datos MongoDB con índices
2. ✅ Autenticación segura con httpOnly cookies (refresh) + JWT en memoria (access)
3. ✅ Token rotation y versionado para seguridad
4. ✅ Registro usuario multi-step
5. ✅ Login con validación de estado PENDING
6. ✅ Panel admin con aprobación de usuarios
7. ✅ **Reset manual de contraseña por admin** (contraseña temporal 72h)
8. ✅ Página forzada para cambiar contraseña temporal
9. ✅ CRUD choferes
10. ✅ Creación hojas de ruta con validaciones
11. ✅ Numeración secuencial atómica por usuario/año
12. ✅ Anulación de hojas (soft delete)
13. ✅ Histórico con filtros
14. ✅ Generación PDF (ReportLab) con marca de agua para anuladas
15. ✅ Configuración global editable
16. ✅ Admin hardening (credenciales via env vars en producción)
17. ✅ Rate limiting en login admin
18. ✅ UI responsive (PWA-ready)
19. ✅ **Retención automatizada**: Endpoint interno con token técnico, lock de concurrencia, logging con stats_after
20. ✅ **Auditoría de resets**: Logs con admin, user, timestamp, IP. UI en modal de usuario. NUNCA se guarda contraseña.
21. ✅ **Cambio contraseña usuario**: Tab Seguridad en /app/configuracion. Invalida sesión (token_version++) y limpia cookie.

## Backlog P0 (Próximos pasos)
1. ⬜ Logo FAST real en assets

## Backlog P1
1. ⬜ Validadores Pydantic más estrictos (strip, empty->None, extra="forbid")
2. ⬜ Exportar PDF por rango de fechas (endpoint existe, falta UI completa)

## Backlog P2
1. ⬜ Convertir a React Native (Expo)
2. ⬜ Estadísticas dashboard admin
3. ⬜ Exportar datos a CSV

## Credenciales de Desarrollo
- **Admin**: usuario `admin`, contraseña `admin123`
- **MongoDB**: MONGO_URL en .env
- **Email**: Deshabilitado (reset manual por admin)
- **Seguridad producción**: ADMIN_USERNAME y ADMIN_PASSWORD_HASH en variables de entorno
- **Token retención**: RETENTION_JOB_TOKEN en .env (para schedulers externos)

## Notas Técnicas Importantes
1. **Autenticación con cookies**: El refresh token está en una cookie httpOnly. El frontend no lo almacena.
2. **Email deshabilitado**: `/api/auth/forgot-password` y `/api/auth/reset-password` devuelven 410 Gone.
3. **Pruebas locales**: La persistencia de sesión solo funciona correctamente usando la URL de preview, no localhost:3000.
4. **Admin en producción**: Requiere `ADMIN_USERNAME` y `ADMIN_PASSWORD_HASH` en las variables de entorno.
5. **Retención automatizada**: El endpoint `/api/internal/run-retention` requiere header `X-Job-Token` con el valor de `RETENTION_JOB_TOKEN`. Usar desde GitHub Actions o cron externo.

## Cómo configurar Scheduler Externo (GitHub Actions)
```yaml
# .github/workflows/retention-job.yml
name: Daily Retention Job
on:
  schedule:
    - cron: '30 3 * * *'  # 03:30 UTC diario
jobs:
  run-retention:
    runs-on: ubuntu-latest
    steps:
      - name: Execute Retention
        run: |
          curl -X POST "${{ secrets.APP_URL }}/api/internal/run-retention" \
            -H "X-Job-Token: ${{ secrets.RETENTION_JOB_TOKEN }}"
```
