from threading import Thread, Lock
import echolib
import echocv
from echolib import pyecho
import time

import numpy as np

class EcholibHandler:
    """
    EcholibHandler is responsible for handling the
    between process communication, utilizing Echolib.
    
    Attributes
    ----------

    self.docker_publisher: echolib.Publisher
        A publisher on the "dockerIn" channel. Commands in
        the form of a string are sent to the dockerManager.
        Command structure is "<open/close> <demos[demoKey]["cfg"]["dockerId"]>"
        where open/close is denoted by 1, -1 respectively.
        Using this one can open and close a specific container
        denoted by an id, which is stored in the demo's 
        corresponding cfg.xml file.

    self.docker_subscriber: echolib.Subscriber
        A subscriber to the "dockerOut" channel. Responses
        to commands sent over "dockerIn" are recieved on this
        channel. The response contains the string names of
        channels through which communication with the demo
        container is going to take place. One string contains
        the name of the channel from which container results
        can be read, the other denotes the channel through
        which commands can be sent to the demo container.

    self.docker_channel_ready_sub: echolib.Subscriber
        A subscriber to the "containerReady" channel. The
        initiated demo container sends a ready signal when
        it is prepaired to send and recieve data.

    self.docker_camera_stream: echolib.Subscriber
        A subscriber to the "cameraStream" channel. Images
        in RGB format, read from the demo system camera are
        broadcasted on this channel from the camera container.

    """

    def __init__(self):

        self.loop   = echolib.IOLoop()
        self.client = echolib.Client()
        self.loop.add_handler(self.client)

        self.docker_publisher    = echolib.Publisher(self.client,  "dockerIn",  "string")
        self.docker_subscriber   = echolib.Subscriber(self.client, "dockerOut", "string", self.__callback_command)
        self.docker_camera_stream = echolib.Subscriber(self.client, "camera0", "numpy.ndarray", self.__callback_camera_stream)
        self.docker_stopped = pyecho.Subscriber(self.client, "docker_stoped", "string", self.__callback_stop)

        self.docker_camera_stream_lock = Lock()
        self.docker_camera_stream_image_new = False
        self.docker_camera_stream_image   = None
        self.docker_camera_stream_counter = 0

        self.docker_image_lock = Lock()
        self.docker_image_new  = False
        self.docker_image      = None

        self.docker_commands_lock = Lock()
        self.docker_commands     = []

        self.docker_channel_in       = None
        self.docker_channel_out      = None
        self.docker_channel_ready_sub = echolib.Subscriber(self.client, "containerReady", "int", self.__callback_ready)
        self.docker_channel_ready    = False

        self.running = True

        self.handler_thread = Thread(target = self.run)
        self.handler_thread.start()

        self.n_ready = 0

        #self.run()

    def run(self):
        
        while self.loop.wait(10) and self.running:
	    
            self.docker_commands_lock.acquire()
            if len(self.docker_commands) > 0:
                
                command = self.docker_commands.pop(0)

                print("Processing command -> {}".format(command[1]))
                
                writer = echolib.MessageWriter()
                if type(command[1]) is str:
                    writer.writeString(command[1])
                elif type(command[1]) is int:
                    writer.writeInt(command[1])

                command[0].send(writer)
        
            self.docker_commands_lock.release() 
            time.sleep(0.01)
            
    def append_command(self, command):

        self.docker_commands_lock.acquire()
        self.docker_commands.append(command)
        self.docker_commands_lock.release()

    def get_image(self):

        image = self.docker_image if self.docker_image_new else None
        self.docker_image_new = False

        return image

    def set_image_to_none(self):

        self.docker_image_new = False
        self.docker_image    = None

    def get_camera_stream(self):
        
        image = self.docker_camera_stream_image if self.docker_camera_stream_image_new else None
        self.docker_camera_stream_image_new = False

        return image

    def __callback_image(self, message):
        
        #self.docker_image    = _echo.readTensor(echolib.MessageReader(message))
        self.docker_image = echocv.readMat(pyecho.MessageReader(message))
        self.docker_image_new = True

    def __callback_ready(self, message):

        # TODO Perhaps doing this in a thread unsafe way? Might not matter
        self.docker_channel_ready = True 
        self.n_ready += 1

        print(f"Demo container ready signal {self.n_ready}...")

    def __callback_camera_stream(self, message):
        
        self.docker_camera_stream_counter += 1
        self.docker_camera_stream_image = echocv.readMat(pyecho.MessageReader(message))

        self.docker_camera_stream_image_new = True

    def __callback_command(self, message):
        
        channels = echolib.MessageReader(message).readString().split(" ")

        print("Docker manager callback {}".format(channels))

        self.docker_channel_in    = echolib.Subscriber(self.client, channels[0], "numpy.ndarray", self.__callback_image)
        self.docker_channel_out   = echolib.Publisher(self.client, channels[1], "int")

    def __callback_stop(self, message):

        stopped_container = echolib.MessageReader(message).readString()
        
        print(f"Container {stopped_container} stopped...")

        self.docker_image = None
        self.docker_image_new = False