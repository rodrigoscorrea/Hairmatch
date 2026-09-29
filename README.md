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
