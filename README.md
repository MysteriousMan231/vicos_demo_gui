# vicos_demo_gui

Vicos demo framework based on an opensource [Python OpenGL user interface library](https://github.com/MysteriousMan231/opengl_gui).
The Vicos demo framework also depends on the [Echolib opensource inter process comunication library](https://github.com/vicoslab/echolib)
and on a collection of [docker images containing machine vision demos](https://github.com/MysteriousMan231/vicos_demo_dockers).

Also depends on the docker Python api that can be installed by executing
```
pip3 install docker
```

# Setup

## Step 1.
Download, build, and install the Echolib library.
Run the generated echodeamon binary.

## Step 2.
Download and install the OpenGL user interface library and all its' dependencies.

## Step 3.
Download and build all the docker demo images. 
Select a camera docker image to build depending on the camera system you are using (allied_vision/flycapture: do not build both).

## Step 4.
Go into your vicos_demo_gui folder and execute
```
./camera_docker.sh
```
Make sure you have substituted the IMAGEID value inside camera_docker.sh with 
the corresponding id number of the camerafeed docker image generated in Step 3.
Inside the docker image shell execute
```
python3 camera.py
```

## Step 5.
In the vicos_demo_gui folder run two separate processes
```
python3 docker_manager.py
python3 gui_main.py
```
