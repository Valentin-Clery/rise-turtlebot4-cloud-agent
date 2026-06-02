# 🤖 TurtleBot 4 — Hybride Cloud Agent & Digital Twin Stack

> **Stack Technique :** Ubuntu 24.04 · ROS2 Jazzy · FastAPI · Docker Compose · Ultralytics YOLOv8 · Groq API (Llama 3.1) · Tailscale VPN

Ce dépôt contient l'architecture logicielle d'un agent robotique hybride intégrant un grand modèle de langage (LLM) et de la vision par ordinateur (YOLO) pour le contrôle par langage naturel d'un TurtleBot 4. L'intelligence lourde (Raisonnement LLM et inférence YOLO) est déportée sur un serveur Cloud (Scaleway), tandis que l'exécution des commandes physiques peut s'interfacer sur un simulateur ou un robot physique (Jumeau Numérique).

---

## 📁 Structure du Projet

```text
rise-turtlebot4-cloud-agent/
├── .env                  # Clés secrètes (GROQ_API_KEY) - Ignoré par Git
├── docker-compose.yml    # Orchestrateur multi-conteneurs pour le Cloud
├── README.md             # Documentation du projet
├── agent/
│   ├── Dockerfile        # Image de l'Agent intelligent (ROS2 + Python Stack)
│   ├── agent_cloud.py    # Nœud maître asynchrone orchestré par FSM
│   ├── fsm.py            # Moteur de machine à états finis custom
│   ├── toolbox.py        # Outils de Function Calling (génération d'actions ROS2)
│   ├── yolo_node.py      # Service ROS2 d'inférence de vision YOLOv8
│   ├── dbgYoloServ.py    # Client de test et de visualisation YOLO
│   └── requirements.txt  # websockets, openai, numpy, ultralytics
└── web_server/
    ├── Dockerfile        # Image du serveur Web léger (FastAPI)
    ├── web_server.py     # Backend API REST & Passerelle ROS2
    └── templates/
        └── index.html    # Dashboard de contrôle (Visualisation SLAM, vidéo, Chat)
```

---

## 1. Guide d'utilisation avec le serveur

---

## 2. LLM + Function calling + YOLO

---

## 3. Initialisation avec un serveur custom