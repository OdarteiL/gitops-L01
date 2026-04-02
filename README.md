# Lab 01 — GitOps with ArgoCD on KIND

A complete GitOps workflow where every commit to this repository automatically triggers a Kubernetes deployment via ArgoCD.

## The GitOps Loop

```
commit → detect → sync → deploy
```

## Stack

- **KIND** — local Kubernetes cluster running in Docker
- **ArgoCD** — GitOps continuous delivery engine
- **GitHub** — single source of truth for cluster state

## Guide

See [GUIDE.md](./GUIDE.md) for the full step-by-step walkthrough.
