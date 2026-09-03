FROM nvidia/cuda:12.0.1-base-ubuntu22.04

ENV BLENDER_VERSION 4.2
ENV PYTHON_VERSION 3.11
ENV BLENDER_URL https://download.blender.org/release/Blender$BLENDER_VERSION/blender-$BLENDER_VERSION.3-linux-x64.tar.xz
ENV MINICONDA_URL https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
ENV USERNAME anadev
ENV USER_UID 1000
ENV USER_GID $USER_UID
ENV DEBIAN_FRONTEND=noninteractive

# Create the anadev user
RUN groupadd --gid $USER_GID $USERNAME && \
    useradd --uid $USER_UID --gid $USER_GID -m $USERNAME && \
    apt-get update && \
    apt-get install -y sudo && \
    echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME && \
    chmod 0440 /etc/sudoers.d/$USERNAME && \
    cd /home/$USERNAME/

USER $USERNAME

# Install base packages + GCC 12. 
# Added bzip2 and xz-utils here to handle manual extractions later.
RUN sudo apt-get clean && \
    sudo rm -rf /var/lib/apt/lists/* && \
    sudo sed -i 's|http://archive.ubuntu.com/ubuntu/|http://mirrors.kernel.org/ubuntu/|g' /etc/apt/sources.list && \
    sudo apt-get update -o Acquire::Retries=5 && \
    sudo apt-get install -y apt-transport-https ca-certificates curl wget bzip2 \
    gcc gcc-12 g++-12 libstdc++6 gnupg2 xz-utils libgl1-mesa-dev libglu1-mesa \
    libxi6 libxrender1 && \
    sudo apt-get install -y --only-upgrade libstdc++6

# Add Docker CE apt keyring
RUN sudo install -m 0755 -d /etc/apt/keyrings && \
    sudo wget -qO /etc/apt/keyrings/docker.asc https://download.docker.com/linux/ubuntu/gpg && \
    sudo chmod a+r /etc/apt/keyrings/docker.asc && \
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu jammy stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker CE + s3fs
RUN sudo apt-get update && \
    sudo apt-get install -y docker-ce s3fs && \
    sudo apt-get autoremove -y && \
    sudo rm -rf /var/lib/apt/lists/*

# Install Blender and Miniconda
RUN cat /etc/fuse.conf >> /home/$USERNAME/fuse.conf && \
    echo "user_allow_other" >> /home/$USERNAME/fuse.conf && \
    sudo mv /home/$USERNAME/fuse.conf /etc/fuse.conf && \
    sudo mkdir /usr/local/blender && \
    sudo wget "$BLENDER_URL"

RUN sudo tar -xf blender*.xz -C /usr/local/blender --strip-components=1 && \
    sudo rm blender*.xz && \
    sudo mkdir -p /usr/local/blender/$BLENDER_VERSION/scripts/addons && \
    sudo wget -O /usr/local/blender/$BLENDER_VERSION/scripts/addons/blender_mcp_addon.py \
        https://raw.githubusercontent.com/ahujasid/blender-mcp/main/addon.py && \
    sudo wget "$MINICONDA_URL" && \
    sudo chmod +x ./Miniconda3-latest-Linux-x86_64.sh  && \
    sudo ./Miniconda3-latest-Linux-x86_64.sh -b -p /home/$USERNAME/miniconda3 && \
    sudo rm ./Miniconda3-latest-Linux-x86_64.sh && \
    /home/$USERNAME/miniconda3/bin/conda init

# Configure Conda and create the Anatools environment
# FIX: Added libstdcxx-ng=13.2.0 to provide CXXABI_1.3.15
# Added -c conda-forge to ensure libstdcxx-ng=13.2.0 is found
# Added 'pip' to the package list
RUN sudo chown -R $USER_UID:$USER_GID /home/$USERNAME/miniconda3/ && \
    /home/$USERNAME/miniconda3/bin/conda config --set channel_priority flexible && \
    /home/$USERNAME/miniconda3/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main && \
    /home/$USERNAME/miniconda3/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r && \
    /home/$USERNAME/miniconda3/bin/conda create -p /home/$USERNAME/miniconda3/envs/anatools \
        -c conda-forge \
        python=$PYTHON_VERSION pip pyyaml pytest numpy imageio opencv libstdcxx-ng=13.2.0 -y

RUN /home/$USERNAME/miniconda3/envs/anatools/bin/pip install anatools && \
    /home/$USERNAME/miniconda3/bin/pip install anatools && \
    /home/$USERNAME/miniconda3/bin/conda clean -afy && \
    sudo ln -s /home/$USERNAME/miniconda3/envs/anatools /usr/local/miniconda3 && \
    sudo rm -rf /usr/local/blender/$BLENDER_VERSION/python && \
    sudo ln -s /home/$USERNAME/miniconda3/envs/anatools /usr/local/blender/$BLENDER_VERSION/python && \
    echo "conda activate anatools" >> /home/$USERNAME/.bashrc

# GUI and X11 dependencies
RUN sudo apt-get update && sudo apt-get install -y \
    xvfb \
    libx11-6 libxext6 libxrender1 libxkbcommon0 \
    libxi6 libxrandr2 libxfixes3 libxcursor1 libxinerama1 libxxf86vm1 \
    libglu1-mesa libgl1-mesa-glx libegl1 \
    libwayland-client0 libwayland-server0 libwayland-egl1 \
    libdbus-1-3 libsm6 libice6

# FIX: Prioritize the Conda environment lib path to avoid the system's old libstdc++
ENV LD_LIBRARY_PATH=/home/anadev/miniconda3/envs/anatools/lib:/usr/lib/x86_64-linux-gnu:/usr/lib/gcc/x86_64-linux-gnu/12:$LD_LIBRARY_PATH
ENV PATH /usr/local/blender:/usr/local/miniconda3/bin:$PATH