FROM osrf/ros:jazzy-desktop-full

# Éviter les invites interactives lors de l'installation
ENV DEBIAN_FRONTEND=noninteractive

# Mise à jour et installation des paquets indispensables pour le TurtleBot 4 et la vidéo
RUN apt-get update && apt-get install -y \
    ros-jazzy-turtlebot4-simulator \
    ros-jazzy-turtlebot4-desktop \
    ros-jazzy-web-video-server \
    ros-jazzy-rosbridge-suite \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

# Configuration du workspace ROS 2
WORKDIR /ros2_ws

# Source automatique de ROS 2 à l'ouverture du terminal
RUN echo "source /opt/ros/jazzy/setup.bash" >> /root/.bashrc

CMD ["bash"]