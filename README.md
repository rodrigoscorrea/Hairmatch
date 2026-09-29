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
