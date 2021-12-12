from opengl_gui.gui_components import *

import time

def get_scene(parameters):
    
    vicos_red  = [226.0/255, 61.0/255, 40.0/255.0, 0.75]

    parameters.state.polyp_detection_time    = None
    parameters.state.polyp_waiting_detection = False


    def get_docker_texture(gui: Gui, state):

        echolib_handler = state.echolib_handler

        if not echolib_handler.docker_channel_ready:
            return None

        frame        = echolib_handler.get_image()
        camera_image = echolib_handler.get_camera_stream()

        if frame is not None:
            state.polyp_detection_time = time.time()

        if state.polyp_detection_time is None or time.time() - state.polyp_detection_time > 5.0:
            state.polyp_detection_time = None

            print("Returning camera frame...")

            return camera_image

        return frame

    def toggle_detection(button: Button, gui: Gui, state):

        echolib_handler = state.echolib_handler

        if echolib_handler.docker_channel_out is not None:

            parameters.state.polyp_waiting_detection = True
            echolib_handler.append_command((echolib_handler.docker_channel_out, 1))

    button_scale = 1.4
    button_detection = Button(
        colour   = vicos_red,
        position = [0.44, 0.92],
        scale    = [0.10*button_scale, 0.03*button_scale],
        on_click = toggle_detection,
        id       = "demo_toggle_detection_button")

    button_text = TextField(
        colour   = [1.0, 1.0, 1.0, 1.0],
        position = [0.25, 0.65,],
        text_scale = 0.5,
        aspect_ratio = parameters.aspect, 
        id       = "demo_toggle_text")
    button_text.set_text(text = "Preštej polipe", font = parameters.font)
    button_text.center_x()
    button_text.center_y()

    button_text.depends_on(element = button_detection)

    return {"get_docker_texture": get_docker_texture, "elements": [button_detection]}