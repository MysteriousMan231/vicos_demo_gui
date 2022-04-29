from threading import Thread, Lock

import echolib
from echolib.camera import FrameSubscriber

import time
import numpy as np

class EcholibHandler:

    def __init__(self):

        self.loop   = echolib.IOLoop()
        self.client = echolib.Client()
        self.loop.add_handler(self.client)

        # docker_publisher is used to send commands to the docker manager process (starting demos). 
        # docker_subscriber is used to recieve feedback from docker manager process.
        # docker_stopped is used by the docker manager to report when a docker demo has been stopped.

        self.docker_publisher  = echolib.Publisher(self.client,  "dockerIn",      "string")
        self.docker_subscriber = echolib.Subscriber(self.client, "dockerOut",     "string", self.__callback_command)
        self.docker_stopped    = echolib.Subscriber(self.client,  "docker_stoped", "string", self.__callback_stop)

        ###########################

        # Structures used for interfacing with the 
        #
        #

        self.camera_stream = FrameSubscriber(self.client, "camera_stream_0", self.__callback_camera_stream)
        self.camera_stream_output = echolib.Subscriber(self.client, "camera_stream_0_output", "string", self.__callback_camera_stream_output)
        self.camera_stream_input  = echolib.Publisher(self.client,  "camera_stream_0_input",  "string")

        self.docker_camera_ranges = None

        self.camera_stream_image_new = False
        self.camera_stream_image   = None
        self.camera_stream_counter = 0

        ###########################

        self.docker_image_new = False
        self.docker_image     = None

        self.commands_lock = Lock()
        self.docker_commands = []
        self.camera_commands = []

        self.docker_channel_in  = None
        self.docker_channel_out = None
        self.docker_channel_ready_sub = echolib.Subscriber(self.client, "containerReady", "int", self.__callback_ready)
        self.docker_channel_ready = False

        self.running = True

        self.loop.wait(100)

        self.handler_thread = Thread(target = self.run)
        self.handler_thread.start()

        self.n_ready = 0

    def run(self):
        
        while self.loop.wait(10) and self.running:
	    
            self.commands_lock.acquire()
            if len(self.docker_commands) > 0:
                
                command = self.docker_commands.pop(0)

                print(f"Processing docker command -> {command[1]}")
                
                writer = echolib.MessageWriter()
                if type(command[1]) is str:
                    writer.writeString(command[1])
                elif type(command[1]) is int:
                    writer.writeInt(command[1])

                command[0].send(writer)

            if len(self.camera_commands) > 0:
                
                command = self.camera_commands.pop(0)

                print(f"Processing camera command -> {command}")
                
                writer = echolib.MessageWriter()
                writer.writeString(command)
    
                self.camera_stream_input.send(writer)
        
            self.commands_lock.release() 
            time.sleep(0.01)
            
    def append_command(self, command):

        self.commands_lock.acquire()
        self.docker_commands.append(command)
        self.commands_lock.release()

    def append_camera_command(self, command):

        self.commands_lock.acquire()
        self.camera_commands.append(command)
        self.commands_lock.release()

    ###########################

    def get_image(self):

        image = self.docker_image if self.docker_image_new else None
        self.docker_image_new = False

        return image

    def set_camera_to_none(self):
        
        self.camera_stream_image = None

    def get_camera_stream(self):
        
        image = self.camera_stream_image

        return image

    ###########################

    def __callback_image(self, message):
        
        self.docker_image = message.image
        self.docker_image_new = True

        print("Got demo containter output!")

    def __callback_ready(self, message):

        # TODO Perhaps doing this in a thread unsafe way? Might not matter
        self.docker_channel_ready = True 
        self.n_ready += 1

        #print(f"Demo container ready signal {self.n_ready}...")

    ###########################

    def __callback_camera_stream(self, message):

        print(f"Got image...{self.camera_stream_counter}")
        
        self.camera_stream_counter += 1
        self.camera_stream_image = message.image

        self.camera_stream_image_new = True

    def __callback_camera_stream_output(self, message):

        self.docker_camera_ranges = echolib.MessageReader(message).readString().split(" ")

    ###########################

    def __callback_command(self, message):
        
        channels = echolib.MessageReader(message).readString().split(" ")

        print(f"Docker manager callback {channels}")

        self.docker_channel_in  = FrameSubscriber(self.client,   "docker_demo_output",        self.__callback_image)
        self.docker_channel_out = echolib.Publisher(self.client, "docker_demo_command_input", "int")

    def __callback_stop(self, message):

        stopped_container = echolib.MessageReader(message).readString()
        
        print(f"Container {stopped_container} stopped...")

        self.docker_image = None
        self.docker_image_new = False