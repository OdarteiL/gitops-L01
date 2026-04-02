from diagrams import Diagram, Edge
from diagrams.onprem.client import User
from diagrams.onprem.vcs import Github
from diagrams.onprem.gitops import ArgoCD
from diagrams.onprem.container import K3S as Kubernetes

with Diagram("ArgoCD GitOps Architecture", filename="architecture_diagram", show=False):
    dev = User("Developer")
    repo = Github("GitHub Repo\n(Source of Truth)")
    argocd = ArgoCD("ArgoCD")
    k8s = Kubernetes("Kubernetes\n(Minikube)")

    dev >> repo >> argocd >> k8s
    argocd >> Edge(label="sync", style="dashed") >> repo
