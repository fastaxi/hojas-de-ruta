# Credenciales de prueba (SOLO preview)

## Usuario web/móvil aprobado
- Email: qa_review_jun26@test.com
- Password: QaReview2026!
- Estado: APPROVED

## Admin (preview)
- La contraseña admin real NO está disponible (hash en .env, definido por el usuario).
- Para probar endpoints/panel admin, generar token válido:
  ```bash
  cd /app/backend && python3 -c "from dotenv import load_dotenv; load_dotenv('.env'); from auth import create_admin_token; print(create_admin_token())"
  ```
- Frontend admin: inyectar el token en localStorage con la clave `adminToken` y navegar a /admin.
- Token cacheado en: /app/tests/.admin_token (regenerar si expira)
