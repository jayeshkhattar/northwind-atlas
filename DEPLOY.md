# Atlas — Deploy Runbook

Target: single-node **local Kubernetes** (kind or minikube) — zero cost, no cloud, no VPS. Runs the identical objects used to ship an app at a bank (image → Namespace → Secret/ConfigMap → Deployment with probes + limits → Service → Ingress), so the manifests are the real artifact and port 1:1 to a managed cluster (EKS/AKS/GKE) later.

What local can't give you: a public HTTPS demo URL. Covered at the end — tunnel for a quick link, or reuse these same manifests on a free-tier managed cluster when you want one.

Charter: I write every Dockerfile and manifest; Claude scopes and reviews each step. Do one step, verify, then move on. Never skip the verify.

---

## Prereqs
- Docker installed locally (have it).
- `kubectl` + one local cluster tool: **kind** (lightweight, container-based) or **minikube** (VM/driver-based, has an easy ingress addon). Pick one.
- GitHub account for GHCR — optional locally (see Step 2).

---

## Step 1 — Dockerfile
Containerize the Streamlit app.
- Multi-stage (build deps separate from runtime), pinned base (e.g. `python:3.12-slim`), non-root user, `EXPOSE` the Streamlit port, explicit `CMD`.
- Keep the final stage lean — no dev tooling.

**Verify:** `docker build` succeeds; `docker run` locally serves the app on the mapped port.

---

## Step 2 — Get the image to the cluster
Two options — pick one:
- **Local-only (simplest):** skip a registry. Load the built image straight in — `kind load docker-image atlas:<tag>` or `minikube image load atlas:<tag>`. Deployment uses `imagePullPolicy: Never`.
- **Registry (enterprise-shaped):** tag `ghcr.io/<user>/atlas:<tag>`, push to GHCR, pull with an `imagePullSecret`. Do this if you want the registry step on your resume; otherwise the local load is fine.

**Verify:** image present in the cluster (`kind`/`minikube image ls`) or pullable from GHCR.

---

## Step 3 — Start the cluster
- **kind:** `kind create cluster --name atlas`.
- **minikube:** `minikube start`.

**Verify:** `kubectl get nodes` shows the node `Ready`; `kubectl get pods -A` shows system pods running.

---

## Step 4 — Namespace + Secret + ConfigMap
Keys and config out of the image.
- `Namespace: atlas`.
- `Secret` for API keys (Anthropic, Voyage, OpenRouter, Langfuse) — created from `.env`, never committed.
- `ConfigMap` for non-secret config (host URLs, model names).

**Verify:** `kubectl get secret,configmap -n atlas` shows both; values decode correctly.

---

## Step 5 — Deployment
The workload, review-grade.
- Image from Step 2 (matching `imagePullPolicy`), `imagePullSecret` only if using GHCR.
- Env from Secret + ConfigMap (`envFrom`).
- **Liveness + readiness probes** on the Streamlit health path.
- **Resource requests + limits** (CPU/mem) — review always checks this.
- `replicas: 1` (single node); note it's the knob you'd raise on a real cluster.

**Verify:** `kubectl rollout status` succeeds; pod `Running`, probes passing; `kubectl logs` clean.

---

## Step 6 — Service + Ingress
Expose it inside the cluster and reach it locally.
- `Service` (ClusterIP) targeting the pod port.
- **Ingress controller:** `minikube addons enable ingress` (nginx), or for kind install the nginx ingress manifest.
- `Ingress` routing a host (e.g. `atlas.local`) → the Service. Map that host to the cluster IP in `/etc/hosts`.
- TLS: use a self-signed cert for local HTTPS practice (real Let's Encrypt needs a public domain — deferred to the managed-cluster note below).

**Verify:** `http://atlas.local` (or `minikube service` / `kubectl port-forward`) serves the app.

---

## Step 7 — (Later) CI/CD
Automate build + deploy on push.
- GitHub Actions: build image → push to GHCR → `kubectl apply` / `set image` against a cluster (kubeconfig in Actions secrets).
- Local clusters aren't reachable from Actions — wire this when you move to a managed cluster, or run it against a local cluster via a self-hosted runner.

**Verify:** a commit to main builds, pushes, and rolls out with no manual step.

---

## Getting a public demo URL (when you want one)
- **Quickest:** `kubectl port-forward` + a tunnel (`cloudflared` or `ngrok`) → temporary public HTTPS link over your local cluster. Good for a live screen.
- **Real:** reuse Steps 4-6 manifests unchanged on a free-tier / low-cost managed cluster (GKE Autopilot, EKS, AKS, or a cheap k3s droplet later). cert-manager + Let's Encrypt gives auto-renewing TLS there. This is where a real domain + public cert belong.

---

## What this replicates vs a bank deploy
- **Same:** image build, namespaces, secrets/configmaps, deployments with probes and limits, services, ingress, kubectl workflow, and the manifests themselves (which move to a real cluster unchanged).
- **Not:** managed control plane (EKS/AKS/GKE), multi-node scheduling and autoscaling, public TLS + DNS, network policies / service mesh, org-level RBAC, and CI/CD-to-cluster (until Step 7 on a reachable cluster). Talk to these; don't fake them.