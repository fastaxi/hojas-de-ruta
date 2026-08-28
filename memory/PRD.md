# RutasFast - Product Requirements Document

## Descripción
Aplicación full-stack para taxistas en Asturias, España. Incluye una PWA web responsive, panel de administración y app móvil React Native (Expo).

## Stack Tecnológico
- **Backend:** FastAPI + MongoDB + Motor
- **Frontend Web:** React + Tailwind CSS + Shadcn UI
- **Frontend Móvil:** React Native + Expo
- **PDF:** ReportLab + Pillow
- **CI/CD:** GitHub Actions para jobs programados
- **Builds:** Expo Application Services (EAS)

## Funcionalidades Implementadas

### Autenticación
- ✅ Registro de usuarios con aprobación de admin
- ✅ Login web con cookies httpOnly
- ✅ Login móvil con JWT + refresh token rotation
- ✅ Cambio de contraseña obligatorio
- ✅ Botón de ojo para mostrar/ocultar contraseña (web y móvil)
- ✅ Endpoints devuelven objeto de usuario completo

### Hojas de Ruta
- ✅ Crear hojas de ruta inmutables
- ✅ Campo obligatorio de pasajero(s) en web, móvil y PDF
- ✅ Numeración atómica única por usuario/año
- ✅ Anulación de hojas (soft delete)
- ✅ Historial con paginación
- ✅ Ordenamiento por número de hoja (año + secuencia)
- ✅ Filtro de hojas anuladas
- ✅ Vista detalle con todos los campos incluido pasajeros
- ✅ **3 tipos de recogida:** Aeropuerto (AIRPORT), Otra dirección (OTHER), Asistencia en carretera (ROADSIDE)
- ✅ Validación específica por tipo (vuelo para AIRPORT, empresa para ROADSIDE)

### Empresas de Asistencia (Nuevo - Feb 2026)
- ✅ CRUD completo de empresas de asistencia en web y móvil
- ✅ Campos: nombre, CIF, teléfono contacto, email contacto
- ✅ Snapshot inmutable guardado en hojas de ruta ROADSIDE
- ✅ Validación: debe tener teléfono o email de contacto
- ✅ Selector de empresa al crear hoja tipo ROADSIDE
- ✅ Detalle de hoja muestra empresa de asistencia para tipo ROADSIDE

### Exportación PDF
- ✅ PDF individual con formato oficial FAST
- ✅ PDF múltiple con mismo formato que individual (3 secciones)
- ✅ Campo Pasajero(s) incluido en todas las secciones
- ✅ Marca de agua para hojas anuladas
- ✅ Fechas en formato dd/mm/aaaa HH:MM (Europe/Madrid)
- ✅ **Datos de empresa de asistencia** incluidos en PDF para tipo ROADSIDE

### Panel Admin
- ✅ Login separado con ojo en contraseña
- ✅ Aprobar usuarios pendientes
- ✅ Ver todos los usuarios con paginación (100 por página, "Cargar más")
- ✅ Contador total de usuarios
- ✅ Ver hojas de ruta con campo pasajeros
- ✅ Configuración global del PDF
- ✅ Reset de contraseñas
- ✅ Estado del job de retención
- ✅ Fechas en zona horaria Europe/Madrid

### App Móvil
- ✅ Login/Registro con ojo en contraseña
- ✅ Crear hojas de ruta con campo pasajeros
- ✅ Historial con Ver Hoja (incluye pasajeros) y Ver PDF
- ✅ Compartir PDF funcional
- ✅ Caché offline de PDFs (límite 50)
- ✅ Configuración de perfil
- ✅ Gestión de conductores adicionales
- ✅ Cambio de contraseña
- ✅ **Formulario con 3 tipos de recogida** (Aeropuerto, Otra dirección, Asistencia)
- ✅ **Gestión de empresas de asistencia** (nueva pantalla en Ajustes)
- ✅ **Vista detalle muestra empresa de asistencia** para tipo ROADSIDE

### Responsive Web
- ✅ Formularios adaptativos (1 columna en móvil, 2 en desktop)
- ✅ Campos no se superponen en pantallas pequeñas

### Infraestructura
- ✅ GitHub Actions para job de retención diario
- ✅ Política de retención (ocultar 14 meses, purgar 24 meses)
- ✅ EAS configurado para builds Android
- ✅ Paginación escalable para 800+ usuarios

## Escalabilidad y Seguridad (Feb 2026)
- ✅ Logo PDF optimizado en memoria con lru_cache (decenas de KB vs megas)
- ✅ Generación PDF con asyncio.to_thread (no bloquea event loop)
- ✅ Cache PDF reducido a 7 días (TTL index)
- ✅ Validación conductor_driver_id pertenece al usuario
- ✅ Año para numeración usa timezone Europe/Madrid
- ✅ /api/health no expone previews de hashes
- ✅ Paginación cursor en histórico móvil (scroll infinito, 50 por página)
- ✅ Paginación cursor en histórico web (botón "Cargar más", 50 por página)

## Configuración de Credenciales

Las credenciales NO se almacenan en el repositorio. Configurar mediante variables de entorno:

### Variables Requeridas en Producción
- `JWT_SECRET` - Clave secreta para JWT (mín. 32 caracteres, único por entorno)
- `ADMIN_USERNAME` - Usuario administrador
- `ADMIN_PASSWORD_HASH` - Hash bcrypt de la contraseña admin (usar `htpasswd -nbBC 10 "" <password> | tr -d ':'`)
- `MONGO_URL` - Conexión a MongoDB

### Variables Opcionales
- `ENVIRONMENT` - "production" o "development"
- `COOKIE_SECURE` - "true" en HTTPS
- `COOKIE_SAMESITE` - "lax" o "strict"

### Para Desarrollo Local
En desarrollo (sin `ENVIRONMENT=production`), el sistema usa valores por defecto seguros.
Crear usuarios de test mediante el flujo de registro normal + aprobación admin.

## URLs
- **Web Producción:** https://asturia-taxi.emergent.host
- **Preview:** https://taxi-rescue.preview.emergentagent.com

## Revisión general y fixes (Jun 2026)
Auditoría completa con testing agent (iteraciones 11 y 12, 53 tests pytest + UI Playwright):
- ✅ FIX: crear empresa de asistencia solo con teléfono (la web enviaba email:'' → 422; ahora normaliza a null y el backend también acepta '' desde móvil)
- ✅ FIX: paginación en Admin > Hojas de Ruta ("Cargar más" + contador "X de Y hojas" con X-Total-Count; antes solo se veían 50)
- ✅ FIX CRÍTICO: cursor keyset alineado con el sort (year|seq|_id) en /api/admin/route-sheets y /api/route-sheets; antes ~60% de hojas inalcanzables y duplicados al paginar
- ✅ FIX: migración automática en startup de fechas legacy guardadas como string (31 campos) → BSON date; corrige desfase de 2h y filtros de fecha del admin que devolvían 0 resultados
- ✅ FIX: _ensure_utc_aware también normaliza strings ISO sin timezone
- ✅ FIX: eliminada la ráfaga de 401/AxiosError en consola al recargar (interceptor axios registrado una vez con ref del token) y el AuthContext de usuario ya no llama /auth/refresh en rutas /admin
- ✅ FIX: límites acotados en endpoints admin (Query le=200), error 500 genérico sin fuga de detalles, CORS expose_headers para X-Next-Cursor/X-Total-Count
- ✅ FIX: MONGO_URL añadido a backend/.env (antes dependía del fallback hardcodeado)
- ✅ Filtro Taxista del admin carga todos los usuarios por páginas de 200

## Correcciones del Code Review (Jun 2026 - iteración 13)
Verificado con testing agent: 104/104 tests backend + 17/17 comprobaciones UI.
- ✅ SEGURIDAD: token admin migrado de localStorage a cookie httpOnly `admin_token` (login la setea, nuevo POST /api/admin/logout la limpia; get_current_admin acepta cookie o Bearer como fallback para tests)
- ✅ SEGURIDAD: eliminada la contraseña dev hardcodeada (admin123); fail-closed: sin ADMIN_PASSWORD_HASH no hay login admin en ningún entorno
- ✅ Hooks React: deps corregidas (AdminUsersPage con offsetRef, AdminConfigPage fetchConfig con useCallback); interceptor axios no intenta refresh de usuario en endpoints /admin/
- ✅ Keys estables en listas (RegisterPage steps/conductores con _key, historial de resets por timestamp)
- ✅ Consola limpia: el 401 esperado del bootstrap de sesión ya no se loguea como error
- ℹ️ Falsos positivos del reporte descartados: comparaciones `is None` (correctas en Python), "variables indefinidas" (ruff F821 limpio)
- ⏳ NO aplicado (backlog, sin impacto funcional): división de componentes grandes (ConfiguracionPage 982 líneas, AdminUsersPage, AdminSheetsPage, AdminConfigPage) y de funciones backend largas (create_route_sheet, pdf_generator)
- ⚠️ Tras el deploy, los admins deberán volver a iniciar sesión (el token antiguo de localStorage ya no se usa)

## Preparación de Deployment (Jun 2026 - iteración 14)
Health check del deployment agent: **PASS** (sin bloqueadores). Regresión testing agent: 111 tests passed, sin regresiones.
- ✅ Creado `mobile/.env` (EXPO_PUBLIC_BACKEND_URL, tunnel/packager vars)
- ✅ URL móvil ya no está hardcodeada en `app.json`; `config.js` lee EXPO_PUBLIC_BACKEND_URL y `eas.json` define la URL de producción para builds EAS (los APK nuevos deben compilarse con `eas build`)
- ✅ CORS_ORIGINS="*" (requisito del deployment agent para preview/custom domains; la web es same-origin y las cookies SameSite=lax mitigan el riesgo)
- ✅ ELIMINADO el índice TTL destructivo en route_sheets.purge_at (startup + retry): las hojas ya NUNCA se borran automáticamente por MongoDB; la purga es exclusiva del retention job explícito (GitHub Actions / endpoint admin con dry-run). Migración con drop automático del índice legacy, verificada en BD y logs, sin pérdida de datos (los TTL de tokens/cache/rate-limits se mantienen, son efímeros)

### Hallazgos menores pendientes (no bloqueantes, preexistentes)
- El login web de usuario no tiene rate limiting/lockout (admin 5/5min y móvil 10 sí lo tienen) — recomendable migrar contadores a la colección rate_limits
- Búsqueda del Histórico es client-side (no encuentra hojas no cargadas aún)
- Contraste bajo del footer/píldoras de la Landing sobre la foto

## Tareas Pendientes

### P1 - Próximas
- Dashboard de estadísticas en Admin (hojas creadas, usuarios activos)
- Reemplazar inputs date/datetime nativos (formato mm/dd/yyyy en inglés) por calendario shadcn con locale es y formato dd/mm/aaaa (NuevaHojaPage, HistoricoPage, AdminSheetsPage)

### P2 - Futuras
- Exportar datos a CSV desde admin
- Activar servicio de email (actualmente MOCKED)
- Aprovechar ancho de escritorio en Histórico (hoy limitado a ~360px)
- Indicador del job de retención: diferenciar "no programado" (preview) de "fallo" (muestra 'Crítico' permanente en preview)
- Endpoint ligero de usuarios (id+nombre) para el filtro Taxista si se superan ~2000 usuarios

## Notas Técnicas
- El servicio de email (`email_service.py`) está deshabilitado
- Warning de bcrypt en logs (cosmético, sin impacto)
- Para builds móviles usar Node 18 (no 24)
- Si hay problemas de caché en el navegador, borrar "datos del sitio" no solo caché
