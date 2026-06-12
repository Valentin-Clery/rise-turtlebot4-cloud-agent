# 🤖 TurtleBot 4 — Hybride Cloud Agent & Digital Twin Stack

> **Stack Technique :** Ubuntu 24.04 · ROS2 Jazzy · FastAPI · Docker Compose · Ultralytics YOLOv8 · Groq API (Llama 3.1) · Tailscale VPN

Ce dépôt contient l'architecture logicielle d'un agent robotique hybride intégrant un grand modèle de langage (LLM) et de la vision par ordinateur (YOLO) pour le contrôle par langage naturel d'un TurtleBot 4. L'intelligence lourde (Raisonnement LLM et inférence YOLO) est déportée sur un serveur Cloud (Scaleway), tandis que l'exécution des commandes physiques peut s'interfacer sur un simulateur ou un robot physique (Jumeau Numérique).

---

## 📁 Structure du Projet

```text
rise-turtlebot4-cloud-agent/
│
├── agent/
│   ├── Dockerfile        # Image de l'Agent intelligent (ROS2 + Python Stack)
│   ├── agent_cloud.py    # Nœud maître asynchrone orchestré par FSM
│   ├── fsm.py            # Moteur de machine à états finis custom
│   ├── toolbox.py        # Outils de Function Calling (génération d'actions ROS2)
│   ├── yolo_node.py      # Service ROS2 d'inférence de vision YOLOv8
│   ├── dbgYoloServ.py    # Client de test et de visualisation YOLO
│   └── requirements.txt  # websockets, openai, numpy, ultralytics
│
├── web_server/
│    ├── Dockerfile       # Image du serveur Web léger (FastAPI)
│    ├── web_server.py    # Backend API REST & Passerelle ROS2
│    └── templates/
│        └── index.html   # Dashboard de contrôle (Visualisation SLAM, vidéo, Chat)
│
├── .env                  # Clés secrètes (GROQ_API_KEY) - Ignoré par Git
├── docker-compose.yml    # Orchestrateur multi-conteneurs 'agent' et 'web_server' sur Scaleway
├── README.md             # Documentation du projet
├── .gitignore            # Fichiers à ignorer par Git (clés API, caches)
├── README.md             # Documentation globale du projet
│
└── simulation_locale/              # --- NOUVEAU DOSSIER LOCAL ---
│    ├── .devcontainer/             # Configuration VS Code DevContainer
│    │   ├── devcontainer.json
│    │   └── Dockerfile
│    └── src/                       # Scripts de launch ou nœuds ROS 2 locaux
```

---

## 1. Guide d'utilisation avec le serveur

# Ouvrir un terminal pour se connecter au serveur Cloud :
ssh root@51.158.64.140

# Mettre à jour le serveur
apt update && apt upgrade -y
apt install -y docker.io docker-compose git

# Répertoire du projet
cd /opt/rise-turtlebot4-cloud-agent

# Compilation propre de toute la stack
docker compose build --no-cache

# Lancement des conteneurs
docker compose up -d

# Vérification des conteneurs
docker compose ps

# Build global et simulation
ssh root@51.158.64.140
cd /opt/rise-turtlebot4-cloud-agent

# 1. On build tout proprement une seule fois
docker compose build --no-cache

# On lance en local depuis un conteneur avec VS code
xhost +local:docker
ros2 launch turtlebot4_gz_bringup turtlebot4_gz.launch.py gui:=false
ros2 launch turtlebot4_gz_bringup turtlebot4_gz.launch.py mode:=headless
ros2 launch turtlebot4_gz_bringup turtlebot4_gz.launch.py headless:=true

# Le pont Rosbridge
ssh root@51.158.64.140

# 1. Lancer le web_video_server en arrière-plan (le "&" libère le terminal)
ros2 run web_video_server web_video_server --ros-args -p port:=8080 &

# 2. Lancer ensuite ton rosbridge comme d'habitude
ros2 launch rosbridge_server rosbridge_websocket_launch.xml

# Agent
ssh root@51.158.64.140
cd /opt/rise-turtlebot4-cloud-agent
Pour en sortir sans tuer le conteneur, utilise la combinaison de touches Ctrl + P puis Ctrl + Q

# On lance l'agent au premier plan pour voir ses "print" et le raisonnement de Groq
docker compose up -d cloud_agent

# Interface web
ssh root@51.158.64.140
cd /opt/rise-turtlebot4-cloud-agent

# Lance le serveur web au premier plan
docker compose up -d web_interface

# Url page web
http://51.158.64.140

# Tunnel SSH inversé vers Scaleway
# Elle ouvre une session SSH classique, mais elle dit aussi au serveur Scaleway : "Dès que quelqu'un chez toi (comme l'agent) parle sur ton port 9090, renvoie tout ce flux magiquement vers le port 9090 de mon PC local (où écoute Rosbridge)".
ssh -R 9090:localhost:9090 root@51.158.64.140

ssh -R 9090:localhost:9090 -R 8080:localhost:8080 root@51.158.64.140

---

## 2. LLM + Function calling + YOLO

---

## 3. Initialisation avec un serveur custom