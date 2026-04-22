# Test Credentials - RutasFast

## Test User (Preview Environment)
- Email: test-tz@test.com
- Password: TestPass1234
- Status: APPROVED

## Admin (Development only - falls back if ADMIN_PASSWORD_HASH not set)
- Username: admin
- Password: admin123 (only when IS_PRODUCTION=false AND no ADMIN_PASSWORD_HASH)

## Notes
- Production admin uses ADMIN_PASSWORD_HASH from .env (bcrypt)
- Do NOT commit real credentials to git
