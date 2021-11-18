#! /bin/bash

IMAGEID="48e8fca850a4" # The camera docker image ID
ECHO="/tmp/echo.sock"
FLYCAPUTRECAMERADEVICE="/dev/bus/usb/001"
WEBCAMERA="/dev/video0:/dev/video0"

if [ -e /dev/video0 ]
then
    docker run -it --device=${WEBCAMERA} \
    --device=${FLYCAPUTRECAMERADEVICE}:${FLYCAPUTRECAMERADEVICE} \
    --mount src=${ECHO},target=${ECHO},type=bind --entrypoint=/bin/bash ${IMAGEID}
else
    docker run -it --device=${FLYCAPUTRECAMERADEVICE}:${FLYCAPUTRECAMERADEVICE} \
    --mount src=${ECHO},target=${ECHO},type=bind --entrypoint=/bin/bash ${IMAGEID}
fi
