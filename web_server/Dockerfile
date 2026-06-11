FROM osrf/ros:jazzy-desktop

SHELL ["/bin/bash", "-c"]

# Installation de pip et des dépendances système de base
RUN apt-get update && apt-get install -y python3-pip && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt --break-system-packages

COPY . .

# On source ROS2 avant de lancer le serveur Uvicorn
CMD ["bash", "-c", "source /opt/ros/jazzy/setup.bash && uvicorn web_server:app --host 0.0.0.0 --port 8000"]