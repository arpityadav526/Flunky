# Install with Docker or Kubernetes

The container runs on Linux amd64 and arm64, including Docker Desktop on macOS
(Intel/Apple Silicon) and Windows with Linux containers/WSL2. It includes the API
and CLI. Kubernetes is optional; Docker Compose is the easiest local installation.
A container runtime and network access to download images are required. This does
not install native Flutter, Electron or mobile build toolchains on your host.

## Docker Compose

From this checkout, generate private credentials (the command never overwrites an
existing file). With Python installed, use `python scripts/setup_container.py`
(or `python3` on macOS/Linux). Without host Python, this command works in Bash and
PowerShell from the repository root:

```sh
docker run --rm --mount "type=bind,source=.,target=/workspace" -w /workspace python:3.13-slim python scripts/setup_container.py
docker compose --env-file .env.docker up -d --build --wait --wait-timeout 180
docker compose --env-file .env.docker ps
```

On Linux, add `--user "$(id -u):$(id -g)"` to the setup `docker run` command so
that the generated file belongs to your user. Keep `.env.docker` private; it is
excluded from Git and the image. Do not regenerate the database password after
initialization: PostgreSQL keeps its original password in the persistent volume.

Open http://localhost:8000/docs. `/health` checks the server and `/ready` checks
the database schema. The API migrates the database before starting, and restarts
after a host reboot when Docker starts. PostgreSQL data survives `compose down`.
`compose down -v` permanently removes the database and CLI state.

The API binds to localhost by default. To change the port add `FLUNKY_PORT=8080`
to `.env.docker`. For remote access, add `FLUNKY_BIND_ADDRESS=0.0.0.0` and provide
an HTTPS reverse proxy before using real credentials over the network.

Use a locally installed CLI:

```sh
flunky config profile local
flunky config set api_url http://localhost:8000
flunky doctor
```

Or use the included CLI without installing Python:

```sh
docker compose --env-file .env.docker run --rm cli --version
docker compose --env-file .env.docker run --rm cli register
docker compose --env-file .env.docker run --rm cli login --with-password
docker compose --env-file .env.docker run --rm cli add "My first task"
docker compose --env-file .env.docker run --rm cli list
```

Use password login inside containers; browser approval cannot open your host
browser. The CLI shares the API network namespace and connects over loopback. CLI credentials/cache persist in the
`cli-home` volume. The checkout is mounted at `/workspace`; scaffolding writes
there by default. On Linux, to generate files owned by your host account use:

```sh
docker compose --env-file .env.docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp cli init demo --stack fastapi --directory /workspace --yes
```

Do not use `--install` for generated projects inside this image: stack-specific
Node/Flutter toolchains are separate requirements.

Inspect logs or stop services with:

```sh
docker compose --env-file .env.docker logs --tail=100 api
docker compose --env-file .env.docker down
```

For upgrades, back up PostgreSQL, pull the updated checkout, then run:

```sh
docker compose --env-file .env.docker stop api
docker compose --env-file .env.docker up -d --build --wait --wait-timeout 180
```

The default setup uses one API process because authentication throttling is
in-memory. Do not scale replicas/workers until a shared limiter is implemented.
Mail delivery is disabled because the bundled mailer only writes development
files. Registration/login/tasks work; email verification, password resets, and
verified-email personal access token creation require a real mail adapter.

## Kubernetes

Requirements: a cluster, `kubectl`, and a default StorageClass able to provision
a 5 GiB ReadWriteOnce volume. There is no cloud-provider dependency. For local
Minikube, start a cluster and load the image:

```sh
minikube start
docker build -t flunky:local .
minikube image load flunky:local
```

For a remote cluster, build and push to a registry you control (replace the
example below), then update `images.newName` and `images.newTag` in
`deploy/kubernetes/kustomization.yaml`. Configure imagePullSecrets when using a
private registry.

```sh
docker buildx build --platform linux/amd64,linux/arm64 -t YOUR_REGISTRY/flunky:0.1.0 --push .
```

Generate `.env.docker` as above, verify your intended context with
`kubectl config current-context`, then install:

```sh
kubectl apply -f deploy/kubernetes/namespace.yaml
kubectl -n flunky create secret generic flunky-secrets --from-env-file=.env.docker
kubectl apply -k deploy/kubernetes
kubectl -n flunky rollout status statefulset/db --timeout=180s
kubectl -n flunky rollout status deployment/api --timeout=300s
kubectl -n flunky port-forward service/api 8000:8000
```

Create the secret only on first installation; on upgrades keep the existing
secret. No credentials are stored in manifests. The API waits for PostgreSQL,
runs migrations, then exposes readiness. Recreate strategy and one replica
prevent overlapping automatic migrations during ordinary deployments. Upgrades
have a brief interruption. Use a new immutable image tag for each release, update
the Kustomization, and apply again after backing up the database. Avoid concurrent
manual migrations or scaling this deployment.

The service is internal by default. Port-forward exposes it on localhost; a
public deployment needs your cluster's HTTPS ingress configuration. The API uses
a non-root user, read-only filesystem, resource limits and separate readiness /
liveness probes. The bundled PostgreSQL instance is persistent but is not a
high-availability database; arrange backups or use managed PostgreSQL for that.

Troubleshooting:

```sh
kubectl -n flunky get pods,pvc
kubectl -n flunky logs deployment/api
kubectl -n flunky describe pod -l app=flunky-api
```

A Pending PVC usually means no default StorageClass or insufficient storage.
ImagePullBackOff means the image name/registry access or local image load needs
fixing. A migration failure prevents the API from starting; inspect logs before
retrying. Deleting namespace `flunky` deletes its PVCs and may destroy database
data depending on the storage reclaim policy.

References: [Compose startup ordering](https://docs.docker.com/compose/how-tos/startup-order/)
and [Kubernetes initialization](https://kubernetes.io/docs/tasks/configure-pod-container/configure-pod-initialization/).
