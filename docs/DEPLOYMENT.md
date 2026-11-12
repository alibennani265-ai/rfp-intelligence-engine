# Guide d'Exploitation Docker & Kubernetes

## Stack Docker Compose
- **`qdrant` :** Base vectorielle exposée sur le port `6333` avec volume persistant `qdrant_storage`.
- **`backend` :** Image multi-stage Python 3.11 exécutée sous l'utilisateur non-root `n7user` (port `8000`).
- **`frontend` :** Interface Streamlit connectée au backend via le réseau interne Docker (port `8501`).

## Déploiement Kubernetes (`k8s/deployment.yaml`)
- Namespace dédié `rfp-engine`.
- `PersistentVolumeClaim` de `10Gi` garantissant la survie des index vectoriels au redémarrage des pods.
- Sondes `livenessProbe` et `readinessProbe` configurées sur `GET /health`.
