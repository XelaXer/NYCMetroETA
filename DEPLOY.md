# Deploying NYCMetroETA to k3s

Deploys the `metro_api` FastAPI server to the homelab k3s cluster in the `fort` namespace.
Accessible internally at `http://metro.internal.nyc.xelaxer.com` via Traefik on the local network.

---

## Architecture

```
GitHub push to main
    │
    ├─→ [GitHub-hosted runner] Build & push Docker image to docker.nyc.xelaxer.com/nyc_metro_eta:<sha>
    │
    └─→ [Self-hosted runner: k3s-nyc-fort] kubectl set image → rollout status → auto-rollback on failure
```

The Helm chart lives in `homelab-k3s/charts/nyc-metro-eta/`. Release values at `homelab-k3s/releases/fort/nyc-metro-eta/values.yaml`.

---

## One-Time Setup

### Prerequisites

- `kubectl` configured and pointed at the k3s cluster
- `helm` v3+ installed
- Logged in to `docker.nyc.xelaxer.com` (`docker login docker.nyc.xelaxer.com`)
- The `homelab-k3s` repo cloned locally

---

### Step 1 — Apply the namespace

```bash
cd ~/Development/homelab/homelab-k3s
kubectl apply -f namespaces/fort.yaml
```

---

### Step 2 — Create the imagePullSecret

The cluster needs credentials to pull images from the private registry.

```bash
kubectl create secret docker-registry regcred \
  --docker-server=docker.nyc.xelaxer.com \
  --docker-username=<your-registry-username> \
  --docker-password=<your-registry-password> \
  -n fort
```

> Use the same credentials you use with `docker login docker.nyc.xelaxer.com`.

---

### Step 3 — Create a GitHub PAT for the self-hosted runner

1. Go to **GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)**
2. Generate a new token with **`repo`** scope
3. Create the k8s secret:

```bash
kubectl create secret generic github-runner-secret \
  --from-literal=GITHUB_PAT=<your-pat> \
  -n fort
```

---

### Step 4 — Add GitHub Actions secrets to this repo

In **NYCMetroETA → Settings → Secrets and variables → Actions**, add:

| Secret name         | Value                                |
|---------------------|--------------------------------------|
| `REGISTRY_USERNAME` | Your registry username (e.g. ci-bot) |
| `REGISTRY_PASSWORD` | Your registry password               |

> Create a dedicated `ci-bot` registry user if you haven't already. See the homelab-k3s `runners/README.md` for instructions.

---

### Step 5 — Deploy the self-hosted runner

```bash
cd ~/Development/homelab/homelab-k3s
kubectl apply -f runners/fort-runner.yaml
```

Verify it registered in GitHub:
**NYCMetroETA → Settings → Actions → Runners** — you should see `k3s-nyc-fort` with a green idle status.

---

### Step 6 — Initial Helm deploy

```bash
cd ~/Development/homelab/homelab-k3s
./scripts/deploy-nyc-metro-eta.sh
```

---

### Step 7 — Add a local DNS entry

Point `metro.internal.nyc.xelaxer.com` at the Traefik LoadBalancer IP (check with `kubectl get svc -n kube-system traefik`).

Add to Pi-hole or your local DNS server:
```
metro.internal.nyc.xelaxer.com → <Traefik LB IP>
```

---

## Verification

```bash
# Pod is running
kubectl get pods -n fort

# IngressRoute exists
kubectl get ingressroute -n fort

# Health check (after DNS entry)
curl http://metro.internal.nyc.xelaxer.com/health

# Test ETA endpoint (use your arduino_metrodisplay_module/config.json)
curl -s -X POST http://metro.internal.nyc.xelaxer.com/api/eta \
  -H "Content-Type: application/json" \
  -d @arduino_metrodisplay_module/config.json | python3 -m json.tool
```

---

## CI/CD After Setup

Every push to `main` automatically:
1. Builds and pushes a new Docker image tagged with the commit SHA
2. Runs `kubectl set image` on the cluster via the self-hosted runner
3. Waits up to 3 minutes for the pod to become healthy
4. Auto-rolls back if the pod fails to start

---

## Manual Re-deploy

```bash
cd ~/Development/homelab/homelab-k3s
./scripts/deploy-nyc-metro-eta.sh
```
