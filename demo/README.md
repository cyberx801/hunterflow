# HunterFlow demo target

**SYNTHETIC. FOR LOCAL USE ONLY. DO NOT EXPOSE PUBLICLY.**

This directory contains a deliberately inconsistent demo application used for
HunterFlow's automated tests and local demonstrations. It is not a real product;
its flaws exist by design and are documented in `app.py`. HunterFlow must never
present its fixtures as real vulnerability discoveries.

- Users: `alice`, `bob` (role `user`), `carol` (role `admin`)
- Passwords: `<username>-password-123`
- Documented fixtures: unauthenticated read of other users' orders (BOLA), no
  ownership filtering on order listings, admin-only stats endpoint.

Run standalone: `uvicorn app:app --host 0.0.0.0 --port 8080`
Run with HunterFlow: `docker compose --profile demo up -d`
