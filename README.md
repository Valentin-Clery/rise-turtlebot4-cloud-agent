# TurtleBot4 — Workspace ROS2 Jazzy + YOLO + LLM

> Stack : Ubuntu 24.04 · ROS2 Jazzy · NVIDIA GPU · YOLOv8n · Llama 3.2:3b (Ollama)

---

## Structure du projet

```
rise-turtlebot4-cloud-agent/
├── .gitignore
├── README.md
├── agent/
│   ├── Dockerfile
│   ├── agent_cloud.py
│   ├── fsm.py
│   ├── toolbox.py
│   └── requirements.txt   ← websockets, openai, numpy
└── web_server/
    ├── Dockerfile
    ├── web_server.py
    ├── templates/
    │   └── index.html     ← Ton interface de dashboard
    └── requirements.txt   ← fastapi, uvicorn
```

---

## 1. Guide d'utilisation avec le serveur

---

## 2. LLM + Function calling + YOLO

---

## 3. Initialisation avec un serveur custom