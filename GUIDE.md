# GitOps with ArgoCD on KIND — Step-by-Step Guide

## Goal
Build a complete GitOps workflow where every commit to a GitHub repository automatically triggers a Kubernetes deployment using ArgoCD on a local KIND cluster.

**The GitOps loop:** `commit → detect → sync → deploy`

---

## Prerequisites

- Docker installed and running
- `kubectl` installed
- A GitHub account with a public repository

---

## Why KIND instead of Minikube?

KIND (Kubernetes IN Docker) runs Kubernetes nodes as Docker containers. It is lighter, faster to spin up, and works well in CI/CD environments. The GitOps concepts are identical — only the cluster bootstrap differs.

---

## Step 1 — Install KIND

```bash
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.22.0/kind-linux-amd64
chmod +x ./kind
sudo mv ./kind /usr/local/bin/kind
kind version
```

**What this does:** Downloads the KIND binary, makes it executable, and moves it to your PATH. `kind version` confirms the install.

---

## Step 2 — Create a KIND Cluster

```bash
kind create cluster --name gitops-lab
```

**What this does:** Spins up a single-node Kubernetes cluster running inside a Docker container. KIND automatically updates your `~/.kube/config` so `kubectl` points to this new cluster.

Verify the cluster is up:

```bash
kubectl cluster-info --context kind-gitops-lab
kubectl get nodes
```

You should see one node in `Ready` state.

---

## Step 3 — Install ArgoCD

ArgoCD is the GitOps engine. It watches your Git repo and reconciles the cluster state to match what is declared there.

```bash
kubectl create namespace argocd

kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

**What this does:**
- Creates a dedicated `argocd` namespace to isolate all ArgoCD components.
- Applies the official ArgoCD manifest which deploys the API server, repo server, application controller, and UI.

Wait for all pods to be running:

```bash
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=120s
kubectl get pods -n argocd
```

---

## Step 4 — Access the ArgoCD UI

KIND does not expose LoadBalancer services externally, so use port-forwarding:

```bash
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

**What this does:** Tunnels traffic from your local port `8080` to the ArgoCD server service inside the cluster. Open `https://localhost:8080` in your browser (accept the self-signed cert warning).

Get the initial admin password:

```bash
kubectl get secret argocd-initial-admin-secret -n argocd \
  -o jsonpath="{.data.password}" | base64 -d && echo
```

Login with username `admin` and the password printed above.

---

## Step 5 — Prepare Your GitHub Repository

Create a GitHub repository (e.g. `gitops-lab-app`) with the following structure:

```
gitops-lab-app/
└── k8s/
    └── deployment.yaml
```

`k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-app
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: demo-app
  template:
    metadata:
      labels:
        app: demo-app
    spec:
      containers:
        - name: demo-app
          image: nginx:1.25
          ports:
            - containerPort: 80
```

**What this does:** This is your "desired state" declaration. ArgoCD will ensure the cluster always matches this file. Changing this file in Git is how you trigger deployments — no `kubectl apply` needed.

---

## Step 6 — Create an ArgoCD Application

This tells ArgoCD which Git repo to watch and where to deploy.

```bash
kubectl apply -f - <<EOF
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: demo-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/<your-username>/gitops-lab-app
    targetRevision: HEAD
    path: k8s
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
EOF
```

**What each field means:**

| Field | Purpose |
|---|---|
| `repoURL` | The GitHub repo ArgoCD monitors |
| `targetRevision: HEAD` | Always track the latest commit on the default branch |
| `path: k8s` | Only look at the `k8s/` folder inside the repo |
| `destination.server` | Deploy into the same cluster ArgoCD runs in |
| `automated.prune: true` | Delete resources from the cluster if removed from Git |
| `automated.selfHeal: true` | Revert any manual `kubectl` changes that drift from Git |

---

## Step 7 — Watch the GitOps Loop in Action

Check the sync status:

```bash
kubectl get application demo-app -n argocd
```

Watch the deployment appear:

```bash
kubectl get pods -n default -w
```

ArgoCD polls the repo every 3 minutes by default. To trigger an immediate sync:

```bash
# Install ArgoCD CLI
curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x argocd && sudo mv argocd /usr/local/bin/

argocd login localhost:8080 --username admin --password <your-password> --insecure
argocd app sync demo-app
```

---

## Step 8 — Trigger a Deployment via Git Commit

Edit `k8s/deployment.yaml` in your GitHub repo — for example, change `replicas: 1` to `replicas: 3` or update the image tag to `nginx:1.26`.

Commit and push the change:

```bash
git add k8s/deployment.yaml
git commit -m "scale to 3 replicas"
git push
```

Within minutes (or immediately after a manual sync), ArgoCD detects the diff and applies the change:

```bash
kubectl get pods -n default
# You will now see 3 pods instead of 1
```

**This is the full GitOps loop:** Git is the single source of truth. No one runs `kubectl apply` manually. The cluster converges to whatever is in Git.

---

## Step 9 — Observe Self-Healing

Try manually deleting a pod or scaling the deployment:

```bash
kubectl scale deployment demo-app --replicas=0 -n default
```

Within seconds, ArgoCD detects the drift and restores the deployment to match Git (`replicas: 3`). This is `selfHeal: true` in action.

---

## Step 10 — Cleanup

```bash
kind delete cluster --name gitops-lab
```

This removes the entire cluster and all resources inside it.

---

## Summary — The GitOps Loop

```
Developer commits to GitHub
        ↓
ArgoCD detects diff (polls every 3 min or via webhook)
        ↓
ArgoCD syncs: applies manifests to Kubernetes
        ↓
Kubernetes reconciles: pods updated/scaled/replaced
        ↓
Cluster state matches Git state ✓
```

Key principles demonstrated:
- Git is the **single source of truth**
- All changes go through **Git commits**, not direct `kubectl` commands
- ArgoCD continuously **reconciles** cluster state to match Git
- `selfHeal` ensures **drift is automatically corrected**
