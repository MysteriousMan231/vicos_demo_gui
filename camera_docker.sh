#! /bin/bash

IMAGEID="a9b15de3412a" # The camera docker image ID
ECHO="/tmp/echo.sock"
WEBCAMERA="/dev/video0:/dev/video0"

FLYCAPUTRECAMERADEVICE="/dev/bus/usb/001"
ALLIEDVISIONDEVICE="/dev/bus/usb/002"

if [ -e /dev/video0 ]
then
    docker run -it --device=${WEBCAMERA} \
    --device=${FLYCAPUTRECAMERADEVICE}:${FLYCAPUTRECAMERADEVICE} \
    --device=${ALLIEDVISIONDEVICE}:${ALLIEDVISIONDEVICE} \
    --mount src=${ECHO},target=${ECHO},type=bind --entrypoint=/bin/bash ${IMAGEID}
else
    docker run -it --device=${FLYCAPUTRECAMERADEVICE}:${FLYCAPUTRECAMERADEVICE} \
    --device=${ALLIEDVISIONDEVICE}:${ALLIEDVISIONDEVICE} \
    --mount src=${ECHO},target=${ECHO},type=bind --entrypoint=/bin/bash ${IMAGEID}
fi
