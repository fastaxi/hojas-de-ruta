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
- ✅ Campo obligatorio de pasajero(s)
- ✅ Numeración atómica única por usuario/año
- ✅ Anulación de hojas (soft delete)
- ✅ Historial con paginación
- ✅ Ordenamiento por número de hoja (año + secuencia)
- ✅ Filtro de hojas anuladas

### Exportación PDF
- ✅ PDF individual con formato oficial FAST
- ✅ PDF múltiple con mismo formato que individual
- ✅ 3 secciones: Titular/Vehículo, Contratación, Servicio
- ✅ Campo Pasajero(s) incluido
- ✅ Marca de agua para hojas anuladas
- ✅ Fechas en formato dd/mm/aaaa HH:MM (Europe/Madrid)

### Panel Admin
- ✅ Login separado
- ✅ Aprobar usuarios pendientes
- ✅ Ver todos los usuarios y hojas
- ✅ Configuración global del PDF
- ✅ Reset de contraseñas
- ✅ Estado del job de retención

### App Móvil
- ✅ Login/Registro
- ✅ Crear hojas de ruta con todos los campos
- ✅ Historial con Ver Hoja y Ver PDF
- ✅ Caché offline de PDFs (límite 50)
- ✅ Compartir PDFs
- ✅ Configuración de perfil
- ✅ Gestión de conductores adicionales
- ✅ Cambio de contraseña

### Infraestructura
- ✅ GitHub Actions para job de retención diario
- ✅ Política de retención (ocultar 14 meses, purgar 24 meses)
- ✅ EAS configurado para builds Android

## Credenciales de Test
- **Admin Web:** admin / qgyq8wx%dq1AvYgQ
- **Usuario Test:** juantest@test.com / Test1234!

## URLs
- **Web:** https://asturia-taxi.emergent.host
- **Preview:** https://rutasfast-2.preview.emergentagent.com

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
