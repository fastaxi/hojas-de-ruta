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

## Lo Implementado ✅
1. ✅ Modelo de datos MongoDB con índices
2. ✅ Autenticación JWT (access + refresh)
3. ✅ Registro usuario multi-step
4. ✅ Login con validación de estado PENDING
5. ✅ Panel admin con aprobación de usuarios
6. ✅ CRUD choferes
7. ✅ Creación hojas de ruta con validaciones
8. ✅ Numeración secuencial por usuario/año
9. ✅ Anulación de hojas (soft delete)
10. ✅ Histórico con filtros
11. ✅ Generación PDF (ReportLab)
12. ✅ Configuración global editable
13. ✅ UI responsive (PWA-ready)

## Backlog P0 (Próximos pasos)
1. ⬜ Job de retención (ocultar 14 meses, purgar 24 meses)
2. ⬜ Configurar RESEND_API_KEY para emails reales
3. ⬜ Logo FAST real en assets
4. ⬜ Validación DNI español (formato)

## Backlog P1
1. ⬜ Exportar PDF por rango de fechas (endpoint existe, falta UI completa)
2. ⬜ Búsqueda avanzada en histórico
3. ⬜ Notificaciones push (opcional)

## Backlog P2
1. ⬜ Estadísticas dashboard admin
2. ⬜ Exportar datos a CSV
3. ⬜ Multi-idioma (descartado por ahora)

## Credenciales de Desarrollo
- **Admin**: usuario `admin`, contraseña `admin123`
- **MongoDB**: localhost:27017, DB: rutasfast_db
- **Email**: Deshabilitado (sin RESEND_API_KEY)
