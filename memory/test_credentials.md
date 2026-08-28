# Credenciales de prueba (SOLO preview)

## Usuario web/móvil aprobado
- Email: qa_review_jun26@test.com
- Password: QaReview2026!
- Estado: APPROVED

## Admin (preview)
- La contraseña admin real NO está disponible (hash en .env, definido por el usuario).
- IMPORTANTE (desde Jun 2026): el panel admin usa cookie httpOnly `admin_token` (ya NO usa localStorage).
- Para probar endpoints admin por API, generar token válido y usarlo como Bearer (fallback soportado) o cookie:
  ```bash
  cd /app/backend && python3 -c "from dotenv import load_dotenv; load_dotenv('.env'); from auth import create_admin_token; print(create_admin_token())"
  # curl con header:  -H "Authorization: Bearer $TOKEN"
  # curl con cookie:  -b "admin_token=$TOKEN"
  ```
- Frontend admin (Playwright): inyectar la cookie httpOnly antes de navegar:
  ```python
  await context.add_cookies([{
      "name": "admin_token", "value": TOKEN,
      "domain": "rutas-staging.preview.emergentagent.com", "path": "/",
      "httpOnly": True, "secure": True
  }])
  ```
  y navegar a /admin (el contexto verifica la sesión con GET /api/admin/config).
- Token cacheado en: /app/tests/.admin_token (regenerar si expira, dura 8h)
- Nota: ya NO existe contraseña dev por defecto (admin123 eliminado, fail-closed sin ADMIN_PASSWORD_HASH).
