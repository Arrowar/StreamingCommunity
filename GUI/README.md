# Web GUI per ricerca e download

## Comandi rapidi:
- Installazione deps: `pip install -r .\GUI\requirements.txt`
- Esecuzione migrazioni: `python GUI/manage.py migrate`
- Avvio dev: `python GUI/manage.py runserver 0.0.0.0:8000`

## Problemi di CSRF
- In caso di problemi quando si effettua una ricerca al di fuori della propria rete (magari sotto un reverse proxy) impostare la variabile d'ambiente `CSRF_TRUSTED_ORIGINS`
    > Esempio: `CSRF_TRUSTED_ORIGINS="http://127.0.0.1:8000 https://altrodominio.it"`
- Se il reverse proxy termina SSL/TLS, abilitare anche il forwarding dello schema HTTPS verso Django:
    > Apache: `RequestHeader set X-Forwarded-Proto "https"`
    > Environment: `SECURE_PROXY_SSL_HEADER_ENABLED=true`
- In deploy dietro proxy conviene impostare anche:
    > `ALLOWED_HOSTS="streaming.hurry-ha.casa"`
    > `USE_X_FORWARDED_HOST=true`
    > `CSRF_COOKIE_SECURE=true`
    > `SESSION_COOKIE_SECURE=true`
