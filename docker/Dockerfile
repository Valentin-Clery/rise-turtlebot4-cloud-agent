FROM osrf/ros:jazzy-desktop

ARG DEBIAN_FRONTEND=noninteractive

# ─────────────────────────────────────────
# Système de base + outils GUI
# libgl1-mesa-glx est obsolète sur Ubuntu 24.04, remplacé par libgl1
# ─────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    git \
    nano \
    vim \
    htop \
    tmux \
    python3-pip \
    python3-dev \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-vcstool \
    build-essential \
    cmake \
    libopencv-dev \
    python3-opencv \
    iputils-ping \
    net-tools \
    iproute2 \
    lsb-release \
    gnupg \
    libgl1 \
    libglu1-mesa \
    libgles2 \
    libglvnd0 \
    libglx0 \
    libegl1 \
    mesa-utils \
    x11-apps \
    ros-jazzy-rosbridge-server \
    ros-jazzy-web-video-server \
    && rm -rf /var/lib/apt/lists/*

# ─────────────────────────────────────────
# Gazebo Harmonic — dépôt OSRF officiel
# Couplé à ROS2 Jazzy
# ─────────────────────────────────────────
RUN curl https://packages.osrfoundation.org/gazebo.gpg \
        --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) \
       signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] \
       http://packages.osrfoundation.org/gazebo/ubuntu-stable \
       $(lsb_release -cs) main" \
       > /etc/apt/sources.list.d/gazebo-stable.list \
    && apt-get update && apt-get install -y --no-install-recommends \
    gz-harmonic \
    && rm -rf /var/lib/apt/lists/*

# ─────────────────────────────────────────
# Paquets ROS2 Jazzy : TurtleBot4 + Simulateur + Nav + SLAM + Caméra
# ─────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    ros-jazzy-turtlebot4-simulator \
    ros-jazzy-turtlebot4-desktop \
    ros-jazzy-turtlebot4-description \
    ros-jazzy-turtlebot4-msgs \
    ros-jazzy-turtlebot4-navigation \
    ros-jazzy-turtlebot4-node \
    ros-jazzy-navigation2 \
    ros-jazzy-nav2-bringup \
    ros-jazzy-slam-toolbox \
    ros-jazzy-image-transport \
    ros-jazzy-image-transport-plugins \
    ros-jazzy-camera-info-manager \
    ros-jazzy-cv-bridge \
    ros-jazzy-vision-opencv \
    ros-jazzy-image-view \
    ros-jazzy-sensor-msgs \
    ros-jazzy-geometry-msgs \
    ros-jazzy-std-msgs \
    ros-jazzy-tf2 \
    ros-jazzy-tf2-ros \
    ros-jazzy-tf2-tools \
    ros-jazzy-rqt \
    ros-jazzy-rqt-common-plugins \
    ros-jazzy-rviz2 \
    ros-jazzy-teleop-twist-keyboard \
    ros-jazzy-ros-gz \
    && rm -rf /var/lib/apt/lists/*

# ─────────────────────────────────────────
# Python : YOLOv8n + client Ollama
# numpy/scipy/Pillow/matplotlib déjà dans l'image de base via apt
# ─────────────────────────────────────────
RUN pip3 install --no-cache-dir --break-system-packages \
        --ignore-installed \
    ultralytics \
    torch \
    torchvision \
    opencv-python-headless \
    requests \
    ollama

# ─────────────────────────────────────────
# Workspace ROS2
# ─────────────────────────────────────────
RUN mkdir -p /tb4_ws/src /tb4_ws/models /tb4_ws/scripts
WORKDIR /tb4_ws

RUN echo "source /opt/ros/jazzy/setup.bash" >> /root/.bashrc \
    && echo "source /tb4_ws/install/setup.bash 2>/dev/null || true" >> /root/.bashrc \
    && echo "export ROS_DOMAIN_ID=42" >> /root/.bashrc \
    && echo "export DISPLAY=\${DISPLAY:-:0}" >> /root/.bashrc \
    && echo "export NVIDIA_VISIBLE_DEVICES=all" >> /root/.bashrc \
    && echo "export NVIDIA_DRIVER_CAPABILITIES=all" >> /root/.bashrc \
    && echo "export __NV_PRIME_RENDER_OFFLOAD=1" >> /root/.bashrc \
    && echo "export __GLX_VENDOR_LIBRARY_NAME=nvidia" >> /root/.bashrc

# ─────────────────────────────────────────
# Variables NVIDIA
# compute,utility  = CUDA / nvidia-smi
# display,graphics = rendu OpenGL Gazebo + RViz sur GPU
# ─────────────────────────────────────────
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility,display,graphics
ENV QT_X11_NO_MITSHM=1
ENV __NV_PRIME_RENDER_OFFLOAD=1
ENV __GLX_VENDOR_LIBRARY_NAME=nvidia

CMD ["/bin/bash"]