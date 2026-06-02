# Image officielle intégrant ROS2 Jazzy Desktop
FROM osrf/ros:jazzy-desktop

# Définition du shell par défaut pour utiliser 'source'
SHELL ["/bin/bash", "-c"]

# Installation des outils indispensables et de Gazebo
RUN apt-get update && apt-get install -y \
    python3-colcon-common-extensions \
    ros-jazzy-rosbridge-suite \
    ros-jazzy-turtlebot4-simulator \
    ros-jazzy-turtlebot4-navigation \
    && rm -rf /var/lib/apt/lists/*

# Création du workspace de simulation sur le serveur
WORKDIR /ros2_cloud_ws
RUN mkdir -p src

# Copie de ton code local (comme ton yolo_node.py) dans le container du serveur
COPY ./agent ./src

# Compilation initiale du workspace
RUN source /opt/ros/jazzy/setup.bash && colcon build --symlink-install

# Configuration du point d'entrée pour sourcer automatiquement ROS2 au démarrage
RUN echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc \
    && echo "source /ros2_cloud_ws/install/setup.bash" >> ~/.bashrc

# Commande par défaut (garde le conteneur actif ou lance un launch-file)
CMD ["bash"]