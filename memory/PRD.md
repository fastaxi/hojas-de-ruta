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

## Tareas Pendientes

### P1 - Próximas
- Dashboard de estadísticas en Admin (hojas creadas, usuarios activos)

### P2 - Futuras
- Exportar datos a CSV desde admin
- Activar servicio de email (actualmente MOCKED)

## Notas Técnicas
- El servicio de email (`email_service.py`) está deshabilitado
- Warning de bcrypt en logs (cosmético, sin impacto)
- Para builds móviles usar Node 18 (no 24)
- Si hay problemas de caché en el navegador, borrar "datos del sitio" no solo caché
