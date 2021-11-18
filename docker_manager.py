from echolib import pyecho
import docker
import time

from threading import Thread, Lock

class DockerManager():

    def __init__(self):
        self.active_container = [None, None]
        self.docker          = docker.from_env()

        self.pyecho_loop   = pyecho.IOLoop()
        self.pyecho_client = pyecho.Client()
        self.pyecho_loop.add_handler(self.pyecho_client)

        self.pyechoDockerIn  = pyecho.Subscriber(self.pyecho_client, "dockerIn", "string", self.__callback)
        self.pyecho_docker_out = pyecho.Publisher(self.pyecho_client, "dockerOut", "string")

        self.command     = None
        self.command_lock = Lock()
        self.stop        = False

        self.pyecho_loop.wait(10)

    def process(self):

        #start = time.time()

        while not self.stop:
            command = None

            #if (time.time() - start) > 1.0:
            #    print("Running container: {}".format(self.active_container[0]))
            #    start = time.time()

            self.command_lock.acquire()
            if self.command is not None:
                command = self.command.split(" ")
                self.command = None
            self.command_lock.release()

            if command is not None:
                
                if command[0] == "1":   # Run container
                    print("Run container with id {}".format(command[1]))

                    for image in self.docker.images.list():
                        
                        if len(image.tags) > 0 and image.tags[0] == command[1]:
                            print("Image with matching tag found...")

                            flag = self.__handle_container(command[1])

                            output_channel = "outContainer" + str(command[0])
                            input_channel  = "inContainer"  + str(command[0])

                            w = pyecho.MessageWriter()
                            w.writeString(output_channel + " " + input_channel)
                            self.pyecho_docker_out.send(w)
                            
                            if flag:

                                self.active_container[0] = command[1]
                                self.active_container[1] = self.docker.containers.run(image.id,\
                                    output_channel + " " + input_channel,\
                                    device_requests=[docker.types.DeviceRequest(count=1, driver="nvidia", capabilities=[['gpu']])],\
                                    remove=True, detach=True,\
                                    volumes = {"/tmp/echo.sock" : {"bind" : "/tmp/echo.sock", "mode" : "rw"}})


                elif command[0] == "-1": # Stop container
                    print("Stopping contianer {}".format(command[1]))
                    self.stopactive_container()

            time.sleep(0.3)
        
    def stopactive_container(self):

        if self.active_container[0] is not None:
            try:
                self.active_container[1].stop()
            except:
                print("Error stopping docker container...")

            self.active_container[0] = self.active_container[1] = None

    def __handle_container(self, tag):
        
        if self.active_container[0] != tag:
            self.stopactive_container()

            return True

        return False

    def __callback(self, message):

        self.command_lock.acquire()
        self.command = pyecho.MessageReader(message).readString()
        print("Got command: {}".format(self.command))
        self.command_lock.release()

def main():
    dm = DockerManager()

    th = Thread(target = dm.process)
    th.start()

    try:
        while dm.pyecho_loop.wait(10):
            time.sleep(0.001)
            
    except KeyboardInterrupt:
        pass

    dm.stop = True
    th.join()

    dm.stopactive_container()
    

if __name__ == '__main__':
    main()