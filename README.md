# Hairmatch
This repository contains the Hairmatch application. The Hairmatch project aims to aid customers finding optimal hairdressers and hair salloons acoording to their preferences and much more

## Running with Docker

All Dockerfiles and the Docker Compose file live under `docker/`. From the repository root:

```
docker compose -f docker/docker-compose.yml --env-file docker/.env up
```


## LocalStack (AWS emulation)

The development environment uses [LocalStack Pro](https://www.localstack.cloud/) (free plan) to emulate AWS (S3 and SES).

1. Create an account at https://app.localstack.cloud and copy your auth token.
2. Set `LOCALSTACK_AUTH_TOKEN` in your `docker/.env` (copy `docker/.env.example`; it has the other `AWS_*`/`S3_*` variables).
3. Start the stack:

```
docker compose -f docker/docker-compose.yml --env-file docker/.env up
```

Check it with `curl http://localhost:4566/_localstack/health` and `aws --endpoint-url http://localhost:4566 s3 ls`.

The bucket and SES identity are created on every boot by `docker/localstack/init/01-resources.sh`. **Data is not persisted**: the free plan does not allow volumes, so everything is lost when the container restarts.

### Media (photos)

Photos are stored in the S3 bucket `S3_BUCKET_NAME` (public read, CORS open to `GET`) instead of `backend/media/`; Django no longer serves `/media/`.

- The backend talks to LocalStack through the docker network (`http://localstack:4566`), while the image URLs returned by the API use `AWS_ENDPOINT_URL` from `docker/.env` (`http://localhost:4566/<bucket>/<key>`), which is what the frontend fetches. On a physical phone or Android emulator `localhost` is the device itself, so set it to your machine's LAN IP (same as `EXPO_PUBLIC_API_BACKEND_URL`).
- Each user's profile photo is stored under its own directory: `profile_pics/<user_id>/<uploaded file>`.
- `populate_hairdressers` uploads each seeded hairdresser's photo (from `backend/users/management/commands/seed_assets/profile_pics/`) just like a regular signup. On every backend boot it re-uploads seeded photos missing from the bucket, so they survive LocalStack restarts. Photos uploaded by users in dev are lost when LocalStack restarts.
- Databases created before this change point to photos that don't exist in the bucket. Reset them with `docker compose -f docker/docker-compose.yml --env-file docker/.env down -v` and start the stack again.

## Cognito local (MiniStack)

E-mail/password accounts authenticate in AWS Cognito. Locally, Cognito runs on [MiniStack](https://github.com/ministackorg/ministack) (`ministackorg/ministack`, MIT, no token needed) in the `ministack` service of the compose file. It is not on LocalStack because the `freemium` license that the free auth token activates does not include `cognito-idp`. S3 and SES stay on LocalStack.

- The MiniStack listens on `http://localhost:4567` (4566 is LocalStack's). The app never talks to Cognito: the backend does, through `AWS_ENDPOINT_URL_COGNITO_IDENTITY_PROVIDER=http://ministack:4566`, which the compose file sets. `AWS_ENDPOINT_URL` keeps pointing S3 at LocalStack.
- `docker/ministack/init/01-cognito.sh` creates the `hairmatch-dev` user pool and the `hairmatch-backend` app client on boot, only when they are missing. The `ministack` service is healthy once the pool exists, and `django` waits for it.
- State is persisted in the `ministack_state` volume, so the pool, the users and the signing key survive restarts.
- `COGNITO_USER_POOL_ID` and `COGNITO_APP_CLIENT_ID` stay empty in dev. The backend then looks the pool and the client up by name.
- List the users with `aws --endpoint-url http://localhost:4567 cognito-idp list-users --user-pool-id <pool id>`, and find the pool id with `aws --endpoint-url http://localhost:4567 cognito-idp list-user-pools --max-results 10`.
- Accounts are confirmed by the backend right after the sign-up, so there is no confirmation code screen. If you confirm an account by hand, the local code is always `123456`.
- `populate_hairdressers` creates the seeded hairdressers in Cognito through the same code as a real signup. Their password is `Senha123`, and on every boot it recreates the ones missing from Cognito.
- **Reset**: `docker compose -f docker/docker-compose.yml --env-file docker/.env down -v` clears Postgres and the MiniStack together. To reset only Cognito, run `docker volume rm hairmatch_ministack_state`; the seed repairs the seeded hairdressers on the next boot, and accounts you created by hand have to be signed up again.
- **Switching from the old login**: accounts created before the Cognito login stored a bcrypt hash and have no Cognito user, so they cannot log in. Reset the database with `down -v` as above.

### User pool in production

The real pool must match the local one, and its IDs go in `COGNITO_USER_POOL_ID` and `COGNITO_APP_CLIENT_ID`:

- sign in with the e-mail (`UsernameAttributes=["email"]`) and `CaseSensitive=false`;
- password policy: at least 8 characters with an upper case letter, a lower case letter and a number, no symbol required;
- an app client without a secret, with `ALLOW_USER_PASSWORD_AUTH` and `ALLOW_REFRESH_TOKEN_AUTH`, an access token valid for 60 minutes and a refresh token valid for 30 days;
- credentials for the backend that allow `AdminConfirmSignUp`, `AdminDeleteUser` and `AdminGetUser` on the pool.
