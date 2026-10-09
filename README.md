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
- `docker/ministack/init/01-cognito.sh` creates the `hairmatch-dev` user pool and the `hairmatch-backend` app client on boot, only when they are missing, and then brings both to the settings in the script (password policy, the verification e-mail, `PreventUserExistenceErrors`). An old `ministack_state` volume gets them on the next boot, and running the script again changes nothing. The `ministack` service is healthy once the pool exists, and `django` waits for it.
- State is persisted in the `ministack_state` volume, so the pool, the users and the signing key survive restarts.
- `COGNITO_USER_POOL_ID` and `COGNITO_APP_CLIENT_ID` stay empty in dev. The backend then looks the pool and the client up by name.
- List the users with `aws --endpoint-url http://localhost:4567 cognito-idp list-users --user-pool-id <pool id>`, and find the pool id with `aws --endpoint-url http://localhost:4567 cognito-idp list-user-pools --max-results 10`.
- An e-mail/password sign-up creates a pending account that must be confirmed with the code Cognito e-mails (see below). The seeded hairdressers are the exception: the seed confirms them itself.
- `populate_hairdressers` creates the seeded hairdressers in Cognito through the same code as a real signup. Their password is `Senha123`, and on every boot it recreates the ones missing from Cognito.
- **Reset**: `docker compose -f docker/docker-compose.yml --env-file docker/.env down -v` clears Postgres and the MiniStack together. To reset only Cognito, run `docker volume rm hairmatch_ministack_state`; the seed repairs the seeded hairdressers on the next boot, and accounts you created by hand have to be signed up again.
- **Switching from the old login**: accounts created before the Cognito login stored a bcrypt hash and have no Cognito user, so they cannot log in. Reset the database with `down -v` as above.

### User pool in production

The real pool must match the local one, and its IDs go in `COGNITO_USER_POOL_ID` and `COGNITO_APP_CLIENT_ID`:

- sign in with the e-mail (`UsernameAttributes=["email"]`) and `CaseSensitive=false`;
- password policy: at least 8 characters with an upper case letter, a lower case letter and a number, no symbol required;
- an app client without a secret, with `ALLOW_USER_PASSWORD_AUTH` and `ALLOW_REFRESH_TOKEN_AUTH`, an access token valid for 60 minutes and a refresh token valid for 30 days;
- `PreventUserExistenceErrors=ENABLED` on the app client, so an unknown e-mail looks like a wrong code or password;
- the verification e-mail and the sender, as described in [E-mail confirmation](#e-mail-confirmation);
- credentials for the backend that allow `AdminConfirmSignUp`, `AdminDeleteUser` and `AdminGetUser` on the pool.

## E-mail confirmation

An e-mail/password sign-up (customer or hairdresser) creates a pending account: `UNCONFIRMED` in Cognito and `is_active=False` in Postgres. Cognito e-mails a 6 digit code, and the app asks for it right after the sign-up. The account can log in, show up in a search or have a session only after `POST /api/auth/email-confirmations` accepts the code. Google accounts skip this, because Google already verified the e-mail.

- `POST /api/auth/email-confirmations` takes `{"email", "code"}`. `POST /api/auth/confirmation-codes` takes `{"email"}`, sends a new code and always answers 202, so it does not tell which e-mails have an account. A login of a pending account answers 403 `email-not-confirmed`, and the app opens the confirmation screen.
- A new sign-up with the e-mail or the phone of a pending account replaces it, in Cognito and in Postgres, so nobody can hold another person's e-mail or phone with an account they never confirmed. A Google sign-in does the same and never links to a pending account.
- Sign-up, confirmation and resend are throttled per IP and per target e-mail (3 sign-ups and 3 resends per e-mail per hour, 10 confirmation attempts per e-mail per hour, 10 confirmations per IP per minute). The counters live in the `hairmatch_cache` table (`DatabaseCache`), which the `users` migration `0011` creates, so every process shares them and a restart keeps them. There is no CAPTCHA.
- `python backend/manage.py purge_unconfirmed_users` deletes the pending accounts older than 7 days (in Cognito first, then in Postgres) and prints `purge_unconfirmed_users deleted=N kept=M`. The backend container runs it on every boot, after the migrations.

### Reading the code in dev

MiniStack delivers the e-mail to its own SES instead of an inbox. Sign up in the app, then read the message:

```
curl -s http://localhost:4567/_ministack/ses/messages
```

The subject is `Hairmatch: confirme seu e-mail`, and the code is always `123456`. Two limits of the emulator: it accepts any code on `ConfirmSignUp`, and it lets an `UNCONFIRMED` user sign in. The backend does not depend on it for the second one (a login of an inactive account answers 403 anyway), and the wrong or expired code cases are covered by the test fake. The seeded hairdressers have no inbox, so the seed confirms them and they log in with `Senha123`.

### Before the launch

The pool in production sends the code through the project's own SES identity. This is an operational step, not code:

- set the pool `EmailConfiguration` to `EmailSendingAccount=DEVELOPER`, with the `SourceArn` of a verified SES identity and a `From` address of Hairmatch. With the default `COGNITO_DEFAULT`, the e-mail does not go through the project's SES and has a low daily quota;
- move the SES account out of the sandbox. In the sandbox, SES delivers only to verified addresses, so real users would not receive the code;
- set the `VerificationMessageTemplate` to `DefaultEmailOption=CONFIRM_WITH_CODE`, with the subject `Hairmatch: confirme seu e-mail` and the message `Seu código de confirmação do Hairmatch é {####}. Ele vale por 24 horas.` (plain text);
- schedule `python backend/manage.py purge_unconfirmed_users` (for example as a Render Cron Job). Until then it only runs when the container boots;
- check, against the real Cognito, the error that `ResendConfirmationCode` returns for a user who is already confirmed. The backend expects `InvalidParameterException` and then reads the user status with `AdminGetUser`, so a different code would make that rare case answer 503.

## API routes

Every route lives under `/api/`. The full list is the Route Table in `.specs/features/api-restful-routes/spec.md`, and `backend/hairmatch/test_routes.py` fails when the URLconf drifts from it.

- Collections are plural nouns (`/api/services`), an item is `/api/services/{id}`, and a child hangs from its parent (`/api/hairdressers/{id}/services`). Filters go in the query (`/api/hairdressers/{id}/available-slots?service=1&date=2026-10-05`, `/api/search?q=`).
- The method carries the verb: `GET` reads, `POST` creates, `PUT` replaces (`/api/services/{id}`, `/api/reviews/{id}`, `/api/hairdressers/{id}/availabilities`), `PATCH` updates part of a resource (`/api/users/me`, `/api/availabilities/{id}`) and `DELETE` removes.
- The logged user is `me`: `/api/users/me`, `/api/customers/me/home`, `PUT` and `DELETE` on `/api/users/me/preferences/{id}`. No route takes an e-mail in the path.
- Session routes stay under `/api/auth/` (`session`, `login`, `logout`, `refresh`, `google`), and the sign-up is `POST /api/users`.
- A path that is not in the table answers 404 `not-found`, and a method it does not list answers 405 `method-not-allowed` with an `Allow` header. Trailing slashes are not redirected.
- The routes changed in one cut, with no `/v1` and no aliases, so the app and the backend ship together.

## Chatbot webhook

The WhatsApp chatbot receives its messages from the Evolution API at `POST /api/chatbot/webhook` (it was `/api/chatbot/test`).

The URL of the webhook is stored in the Evolution API instance, not in this repository, so the code change alone does not move it. Reconfiguring it is a manual step of the production deploy, and it needs explicit authorization for that environment:

1. Deploy the backend that answers `/api/chatbot/webhook`. From that moment `/api/chatbot/test` answers 404, so keep the window between steps 1 and 2 short: messages sent in it are lost.
2. Set the webhook of the `EVOLUTION_INSTANCE_NAME` instance to `<backend url>/api/chatbot/webhook` (Evolution API `POST /webhook/set/{instance}`, or the manager screen).
3. Send a message to the bot and check that it answers.

In development the local instance is pointed at `http://<backend host>:8000/api/chatbot/webhook` the same way.

