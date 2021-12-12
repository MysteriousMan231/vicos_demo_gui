#! /bin/bash

ECHO="/tmp/echo.sock"
CAMERACONFIGFOLDER="/home/vicosdemosystem/Documents/vicos_demo_new/vicos_demo_dockers/camera_docker_allied_vision/config"

FLYCAPUTRECAMERADEVICE="/dev/bus/usb/001"
ALLIEDVISIONDEVICE="/dev/bus/usb"


docker run -it \
--device=${ALLIEDVISIONDEVICE}:${ALLIEDVISIONDEVICE} \
--mount src=${CAMERACONFIGFOLDER},target=/opt/config,type=bind \
--mount src=${ECHO},target=${ECHO},type=bind \
--entrypoint=/bin/bash camerafeed_allied_echolib_old:v1
