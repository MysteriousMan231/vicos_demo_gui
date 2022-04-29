from math import ceil
from venv import create
import numpy as np

import glfw

from opengl_gui.gui_components import *
from opengl_gui.gui_helper     import *

from gui_echolib import EcholibHandler

import xml.etree.ElementTree as ET
import os
from importlib import import_module

class State():

    def __init__(self):

        self.echolib_handler = EcholibHandler()

def load_demos(root: str = "./demos") -> dict:

    demos = {}

    for demo_name in os.listdir(root):
        
        demo_root = root + "/" + demo_name
        demo_has_cfg = False
        demo_has_scene = False

        for demo_files in os.listdir(demo_root):
            demo_has_cfg = demo_has_cfg or demo_files == "cfg.xml"
            demo_has_scene = demo_has_scene or demo_files == "scene.py"

        if demo_has_cfg and demo_has_scene:
            module_path = "demos." + demo_name + "." + "scene"
            module = import_module(module_path)

            xml_valid = [False, False, False, False]
            scene_valid = hasattr(module, "get_scene")

            xml_path = demo_root + "/cfg.xml"
            xml_tree = ET.parse(xml_path)

            xml_cfg_root = xml_tree.getroot()
            xml_parsed = {}

            if xml_cfg_root.tag == "cfg":
                for xml_c in list(xml_cfg_root): # Iterator for children
                    if xml_c.tag == "demoId":
                        xml_parsed[xml_c.tag] = xml_c.text
                        xml_valid[0] = True
                    elif xml_c.tag == "dockerId":
                        xml_parsed[xml_c.tag] = xml_c.text
                        xml_valid[1] = True
                    elif xml_c.tag == "highlight":
                        xml_parsed[xml_c.tag] = xml_c.text
                        xml_valid[2] = True
                    elif xml_c.tag == "video":
                        xml_parsed[xml_c.tag] = demo_root + "/" + xml_c.text
                        xml_valid[3] = True
            xml_valid = all(xml_valid)
                        
            if xml_valid and scene_valid:
                if xml_parsed["demoId"] in demos.keys():
                    print("Duplicated demo id -> {}".format(xml_parsed["demoId"]))
                else:
                    demos[xml_parsed["demoId"]] = {"cfg": xml_parsed, "get_scene": module.get_scene}
            else:
                # TODO better error reporting
                print("{} is not valid.".format(module_path))

    return dict(sorted(demos.items(), key = lambda x: x[1]["cfg"]["highlight"]))

def demo_scene_wrapper(window_aspect_ratio: float, demo_component: dict) -> DisplayTexture:

    camera_aspect_ratio = 4024.0/3036.0

    in_animation = AnimationList(
        transform = ("position", [0.5, 0.0]),
        duration  = 0.75,
        id = "in")

    out_animation = AnimationList(
        transform = ("position", [-2.0, 0.0]),
        duration  = 0.75,
        id = "out")

    display = DisplayTexture(
        position = [2.0, 0.0],
        scale    = [1.0/camera_aspect_ratio, 1.0],
        depth  = 0.95,
        aspect = camera_aspect_ratio,
        animations = {in_animation.id: in_animation, out_animation.id: out_animation},
        id = "demo_display_texture",
        get_texture = demo_component["get_docker_texture"])
    
    for c in demo_component["elements"]:
        c.depends_on(element = display)
    
    display.offset[0] = -1.0/camera_aspect_ratio

    return display

def demo_video_scene(aspect_ratio: float, video: Video, play: np.array, pause: np.array) -> Element:

    play_aspect  = play.shape[1]/play.shape[0]
    base_depth = 0.95
    offset = [-1.0, -1.0]

    play_texture = TextureR(
        position = [0.0, 0.0],
        scale  = [play_aspect*0.085/aspect_ratio, 0.085],
        colour = [1.0, 1.0, 1.0, 1.0],
        id = "play_texture_video",
        get_texture = lambda g, cd: play,
        set_once    = True)

    pause_texture = TextureR(
        position = [0.0, 0.0],
        scale = [play_aspect*0.085/aspect_ratio, 0.085],
        colour = [1.0, 1.0, 1.0, 1.0],
        id = "pause_texture_video",
        get_texture = lambda g, cd: pause,
        set_once    = True)

    def on_click(button: Button, gui: Gui, state: State):

        button.dependent_components.clear()

        if button.mouse_click_count % 2 == 0:

            pause_texture.depends_on(element = button)
            pause_texture.center_x()
            pause_texture.center_y()

            video.resume()
        else:

            play_texture.depends_on(element = button)
            play_texture.center_x()
            play_texture.center_y()

            play_texture.update_geometry(parent = button)

            video.pause()

        print(f"Clicking on button: {button.id}")

    ina = AnimationList(
        transform = ("position", [0.0, 0.0]),
        duration  = 0.75,
        id = "in")

    outa = AnimationList(
        transform = ("position", [-2.0, 0.0]),
        duration  = 0.75,
        id = "out")

    button_in = AnimationList(
        transform = ("position", [None, 0.9]),
        duration  = 1.0,
        id = "button_in")

    button_pause_play = Button(
        colour   = [226.0/255, 61.0/255, 40.0/255.0, 1.0],
        position = [0.2, 2.0],
        scale      = [0.08/aspect_ratio, 0.08],
        on_click   = on_click,
        animations = {button_in.id: button_in},
        shader = "circle_shader",
        id     = "video_button_play_pause")

    pause_texture.depends_on(element = button_pause_play)
    pause_texture.center_x()
    pause_texture.center_y()

    display = DisplayTexture(
        position = [0.0, 0.0],
        scale = [1.0, 1.0],
        get_texture = lambda g, cd: video.get_frame(),
        animations = {ina.id: ina, outa.id: outa},
        id = "traffic_display")

    button_pause_play.depends_on(element = display)
    button_pause_play.center_x()
    button_pause_play.animation_play(animation_to_play = "button_in")

    video.reset_and_play()

    return display


def scene_primary(windowWidth: int, window_height: int, application_state: State, font: dict) -> Element:
    
    camera_aspect_ratio = 4024.0/3036.0

    demos = load_demos()
    demo_videos = {}

    for d in demos:
        video = Video(path = demos[d]["cfg"]["video"], loop = True)
        demo_videos[d] = video

    aspect_ratio = windowWidth/window_height
    icon_width  = int( windowWidth*0.1)
    icon_height = int(window_height*0.1)

    video_icon = rasterize_svg(path = "./res/icons/video-solid.svg",          width = icon_width*1.0, height = icon_height*1.0)
    point_icon = rasterize_svg(path = "./res/icons/hand-pointer.svg",         width = icon_width*0.7, height = icon_height*0.7)
    pause_icon = rasterize_svg(path = "./res/icons/pause-circle-regular.svg", width = icon_width*0.7, height = icon_height*0.7)
    play_icon  = rasterize_svg(path = "./res/icons/play-circle-regular.svg",  width = icon_width*0.7, height = icon_height*0.7)

    vicos_intro_video = Video(path = "./res/vicos.mp4", loop = False)

    video_icon_aspect_ratio = video_icon.shape[1]/video_icon.shape[0]
    point_icon_aspect_ratio = point_icon.shape[1]/point_icon.shape[0]

    white = [1.0, 1.0, 1.0, 1.0]
    vicos_red  = [226.0/255, 61.0/255, 40.0/255.0, 0.75]
    vicos_gray = [85.0/255.0, 85.0/255.0, 85.0/255.0, 0.35]
    vicos_gray_non_transparent = [85.0/255.0, 85.0/255.0, 85.0/255.0, 0.8]
    header_height = 0.05

    display_screen = DemoDisplay(
        position = [0.0, 0.0],
        scale  = [1.0, 1.0],
        depth  = 0.99,
        colour = white,
        id = "base_display_screen")

    intro_fade_out = AnimationListOne(
        transform = ("properties", 0.25),
        duration  = 0.5,
        index = 1,
        id = "fade_out")
    
    intro_fade_in = AnimationListOne(
        transform = ("properties", 1.0),
        duration  = 0.5,
        index = 1,
        id = "fade_in")

    vicos_intro_texture = TextureRGB(
        position = [0.0, 0.0],
        scale    = [1.0, 1.0],
        depth = 0.98,
        alpha = 1.0,
        animations = {intro_fade_out.id: intro_fade_out, intro_fade_in.id: intro_fade_in},
        id = "vicos_intro_texutre",
        get_texture = lambda g, cd: vicos_intro_video.get_frame(),
        set_once = False)

    header_bar = Container(
        position = [0.0, 0.0],
        scale  = [1.0, header_height],
        depth  = 0.97,
        colour = vicos_red,
        id = "header_bar")

    header_bar.depends_on(element = display_screen)
    display_screen.insert_default(element = vicos_intro_texture)
    vicos_intro_video.play()

    header_bar.set_depth(depth = display_screen.properties[0] - 0.02)

    drawer_menu = DrawerMenu(
        position = [0.9, header_height],
        scale    = [1.0, 1.0 - header_height],
        position_opened = [0.55, header_height],
        position_closed = [0.90, header_height],
        id = "drawer_menu")
    drawer_menu_container = Container(
        position = [0.1, 0.0],
        scale = [0.35, 1.0 - header_height],
        colour = vicos_red,
        id = "drawer_menu_container")
    drawer_menu_container.depends_on(element = drawer_menu)

    def calibration_on_grab(component, gui: Gui):

        if len(component.dependent_components[0].dependent_components) > 0:
            return

        for c in create_calibration_menu():
            c.depends_on(element = component.dependent_components[0])
            c.update_geometry(parent = component.dependent_components[0])

    def calibration_on_close(component, gui: Gui):
        component.dependent_components[0].dependent_components.clear()

    drawer_menu_calibration = DrawerMenu(
        position = [0.0, 0.9],
        scale    = [1.0, 1.0 + header_height],
        position_opened = [0.0,-header_height],
        position_closed = [0.0, 0.9],
        id = "drawer_menu_calibration",
        on_grab  = calibration_on_grab,
        on_close = calibration_on_close)
    drawer_menu_calibration_container = Container(
        position = [0.0, 0.0],
        offset   = [0.0, 0.2],
        scale    = [1.0, 1.0],
        colour = vicos_gray_non_transparent,
        id = "drawer_meanu_calibrated_container")

    def create_calibration_menu():

        calibration_title = TextField(
            position = [0.05, 0.05],
            text_scale = 0.68,
            colour = [1.0, 1.0, 1.0, 0.75],
            aspect_ratio = aspect_ratio,
            id = "calibration_title")
        calibration_title.set_text(font = font, text = "Kalibracija kamere")
        calibration_title.center_x()

        # Create live feed component

        def get_original(gui: Gui, state: State):
            return state.echolib_handler.get_camera_stream()

        def get_zoom(gui: Gui, state: State):

            zoom_margin_y = 800
            zoom_maring_x = np.int32(np.floor(zoom_margin_y/camera_aspect_ratio))

            image = state.echolib_handler.get_camera_stream()

            if image is None:
                return None

            return image[zoom_maring_x:-zoom_maring_x, zoom_margin_y:-zoom_margin_y, :]

        def get_display(position, scale, title, get_texture, id):

            calibration_live_feed_container = Container(
                position = position,
                scale    = [scale/camera_aspect_ratio, scale],
                colour = [1.0, 1.0, 1.0, 0.8],
                id = f"calibration_display_container_ {id}") 

            calibration_display_live_feed = DisplayTexture(
                position = [0.1, 0.07],
                scale    = [(scale - 0.01)/camera_aspect_ratio, scale - 0.05],
                aspect = camera_aspect_ratio,
                id = f"calibration_display_{id}",
                get_texture = get_texture)

            calibration_live_feed_title = TextField(
                    position = [0.05, 0.05],
                    text_scale = 0.7,
                    colour = [0.0, 0.0, 0.0, 0.75],
                    aspect_ratio = aspect_ratio, 
                    id = f"calibration_display_title_{id}")

            calibration_live_feed_title.set_text(font = font, text = title)
            calibration_live_feed_title.center_x()

            calibration_live_feed_title.depends_on(element = calibration_live_feed_container)
            calibration_display_live_feed.center_x()

            calibration_display_live_feed.depends_on(element = calibration_live_feed_container)

            return calibration_live_feed_container

        d_original = get_display(position = [0.025, 0.28], scale = 0.62, title = "Originalna velikost", get_texture = get_original, id = 0)
        d_zoom     = get_display(position = [0.51,  0.28], scale = 0.62, title = "Povečana velikost",   get_texture = get_zoom, id = 1)

        button_container = Container(
            position = [0.01, 0.08],
            scale  = [1.0, 0.2],
            depth  = 0.97,
            colour = [1.0, 1.0, 1.0, 0.5],
            id = "button_contianer")

        button_container.command_chain.pop(1)

        button_awb = Button(
            position = [0.025, 0.04],
            offset = [0.0, 0.015*aspect_ratio],
            scale  = [0.22, 0.09],
            colour = vicos_red,
            id = "button_awb")

        button_awb_text = TextField(
            position = [0.0, 0.0],
            text_scale = 0.68,
            colour = [1.0, 1.0, 1.0, 0.75],
            aspect_ratio = aspect_ratio, 
            id = "button_awb_text")
        button_awb_text.set_text(font = font, text = "Samodejna raven beline")
        button_awb_text.center_x()
        button_awb_text.center_y()

        button_awb_text.depends_on(element = button_awb)

        button_ax = Button(
            position = [0.275, 0.04],
            offset = [0.0, 0.015*aspect_ratio],
            scale  = [0.22, 0.09],
            colour = vicos_red,
            id = "button_ax")

        button_ax_text = TextField(
            position = [0.0, 0.0],
            text_scale = 0.68,
            colour = [1.0, 1.0, 1.0, 0.75],
            aspect_ratio = aspect_ratio, 
            id = "button_ax_text")
        button_ax_text.set_text(font = font, text = "Samodejna osvetljitev")
        button_ax_text.center_x()
        button_ax_text.center_y()

        button_ax_text.depends_on(element = button_ax)
   
        def slider_awb_get_range(slider: RangeSlider, custom_data):
            ranges = custom_data.echolib_handler.docker_camera_ranges

            if ranges is None:
                return None

            for i in range(0, len(ranges), 3):

                if ranges[i] == "BalanceRatio":
                    return (float(ranges[i + 1]), float(ranges[i + 2]))

        def slider_ax_get_range(slider: RangeSlider, custom_data):
            ranges = custom_data.echolib_handler.docker_camera_ranges

            if ranges is None:
                return None

            for i in range(0, len(ranges), 3):

                # Halve max exposure time
                if ranges[i] == "ExposureTime": 
                    #return (float(ranges[i + 1]), float(ranges[i + 2]))
                    return (float(ranges[i + 1]), 39062.3407109375)

        slider_awb_to_red = AnimationList(
            transform = ("colour", vicos_red),
            duration  = 0.2,
            id = "slider_awb_to_red")

        slider_awb_to_white = AnimationList(
            transform = ("colour", [1.0, 1.0, 1.0, 1.0]),
            duration  = 0.2,
            id = "slider_awb_to_white")

        slider_ax_to_red = AnimationList(
            transform = ("colour", vicos_red),
            duration  = 0.2,
            id = "slider_ax_to_red")

        slider_ax_to_white = AnimationList(
            transform = ("colour", [1.0, 1.0, 1.0, 1.0]),
            duration  = 0.2,
            id = "slider_ax_to_white")

        slider_awb = RangeSlider(
            position = [0.58, 0.04],
            scale = [0.15, 0.01],
            range_bottom = 0.0,
            range_top    = 1.0,
            colour = vicos_red,
            aspect_ratio = aspect_ratio,
            get_range = slider_awb_get_range,
            id = "range_slider_awb")
        slider_awb.circle.animations = {slider_awb_to_red.id: slider_awb_to_red, slider_awb_to_white.id: slider_awb_to_white}

        slider_ax = RangeSlider(
            position = [0.78, 0.04],
            scale = [0.15, 0.01],
            range_bottom = 0.0,
            range_top    = 1.0,
            colour = vicos_red,
            aspect_ratio = aspect_ratio,
            get_range = slider_ax_get_range,
            id = "range_slider_ax")
        slider_ax.circle.animations = {slider_ax_to_red.id: slider_ax_to_red, slider_ax_to_white.id: slider_ax_to_white}

        slider_awb_text = TextField(
            position = [0.575, 0.3],
            text_scale = 0.68,
            colour = [1.0, 1.0, 1.0, 0.75],
            aspect_ratio = aspect_ratio, 
            id = "slider_awb_text")
        slider_awb_text.set_text(font = font, text = "Raven beline: {:.2f}".format(slider_awb.selected_value))

        slider_ax_text = TextField(
            position = [0.76, 0.3],
            text_scale = 0.68,
            colour = [1.0, 1.0, 1.0, 0.75],
            aspect_ratio = aspect_ratio, 
            id = "slider_ax_text")
        slider_ax_text.set_text(font = font, text = "Čas osvetlitve: {:.3f} ms".format(slider_ax.selected_value*1e-6))

        def slider_awb_on_update(slider: RangeSlider, custom_data):
            slider_awb_text.set_text(font = font, text = "Raven beline: {:.2f}".format(slider.selected_value))

        def slider_ax_on_update(slider: RangeSlider, custom_data):
            slider_ax_text.set_text(font = font, text = "Čas osvetlitve: {:.3f} ms".format(slider.selected_value*1e-6))

        def slider_awb_on_select(slider: RangeSlider, custom_data):
            custom_data.echolib_handler.append_camera_command(f"BalanceRatio {slider.selected_value}")

        def slider_ax_on_select(slider: RangeSlider, custom_data):
            custom_data.echolib_handler.append_camera_command(f"ExposureTime {slider.selected_value}")

        def button_awb_on_click(button: Button, gui: Gui, custom_data):
            
            if button.mouse_click_count % 2:

                slider_awb.circle.animation_play(slider_awb_to_red.id)
                slider_awb.lock()

                button.set_colour(vicos_gray)

                custom_data.echolib_handler.append_camera_command(f"BalanceWhiteAuto Once")
            else:

                slider_awb.circle.animation_play(slider_awb_to_white.id)
                slider_awb.unlock()
    
                button.set_colour(vicos_red)

                custom_data.echolib_handler.append_camera_command(f"BalanceWhiteAuto Off")

        def button_ax_on_click(button: Button, gui: Gui, custom_data):

            if button.mouse_click_count % 2:

                slider_ax.circle.animation_play(slider_ax_to_red.id)
                slider_ax.lock()

                button.set_colour(vicos_gray)

                custom_data.echolib_handler.append_camera_command(f"ExposureAuto Once")
            else:

                slider_ax.circle.animation_play(slider_ax_to_white.id)
                slider_ax.unlock()

                button.set_colour(vicos_red)

                custom_data.echolib_handler.append_camera_command(f"ExposureAuto Off")

        button_awb.on_click = button_awb_on_click
        button_ax.on_click  = button_ax_on_click

        slider_awb.on_value_update  = slider_awb_on_update
        slider_awb.on_select = slider_awb_on_select

        slider_ax.on_value_update  = slider_ax_on_update
        slider_ax.on_select = slider_ax_on_select

        button_awb.center_y()
        button_ax.center_y()
        slider_awb.center_y()
        slider_ax.center_y()

        button_awb.depends_on(element = button_container)
        button_ax.depends_on(element  = button_container)
        slider_awb.depends_on(element = button_container)
        slider_ax.depends_on(element  = button_container)
        slider_awb_text.depends_on(element = button_container)
        slider_ax_text.depends_on(element = button_container)

        return [d_original, d_zoom, calibration_title, button_container]

    drawer_menu_calibration_container.depends_on(element = drawer_menu_calibration)
    
    def hint_constructor():

        x = 0.94
        y = 0.4755

        fade_in = AnimationListOne(
            transform = ("colour", 0.75),
            on_end    = lambda c, g, u: c.animation_play(animation_to_play = "move_0"),
            duration  = 0.25,
            id = "fade_in",
            index = 3)

        fade_out = AnimationListOne(
            transform = ("colour", 0.0),
            duration  = 0.25,
            id = "fade_out",
            index = 3)

        move_0 = AnimationList(
            transform = ("position", [x - 0.02, y]),
            on_end    = lambda c, g, u: c.animation_play(animation_to_play = "move_1"),
            duration  = 2.0,
            id = "move_0")

        move_1 = AnimationList(
            transform = ("position", [x, y]),
            on_end    = lambda c, g, u: c.animation_play(animation_to_play = "move_0"),
            duration  = 0.5,
            id = "move_1")

        pointer_texture = TextureR(
            position = [x, y],
            scale  = [point_icon_aspect_ratio*0.07/aspect_ratio, 0.07],
            depth  = 0.98,
            colour = vicos_red,
            animations = {fade_in.id: fade_in, fade_out.id: fade_out, move_0.id: move_0, move_1.id: move_1},
            id = "hint",
            get_texture = lambda g, cd: point_icon,
            set_once = True)

        pointer_texture.animation_play(animation_to_play = "fade_in")

        return pointer_texture

    hint = hint_constructor()
    hint.depends_on(element = display_screen)

    # Calibration drawer is going to be drawn over hint
    # and over the demo drawer menu
    drawer_menu_calibration.depends_on(element = display_screen)
    drawer_menu.depends_on(element = display_screen)

    #### Construct demos ####

    demo_buttons          = []
    demo_video_buttons    = []
    demo_buttons_position = 0.05

    time_scale = 1.0

    for i in demos.keys():

        video_icon_texture = TextureR(
            position = [0.0, 0.0],
            offset   = [-video_icon_aspect_ratio*0.05/aspect_ratio, 0.05],
            scale    = [ video_icon_aspect_ratio*0.05/aspect_ratio, 0.05],
            colour = white,
            id = "video_icon_{}".format(i),
            get_texture = lambda g, cd: video_icon,
            set_once = True)

        #### Click animation

        main_scale_up = AnimationList(
            transform = ("scale", [0.255, 0.095]),
            on_end = lambda c, g, u: c.animation_play(animation_to_play = "scale_down"),
            duration  = 0.2,
            id = "scale_up")

        main_scale_down = AnimationList(
            transform = ("scale", [0.25, 0.09]),
            duration  = 0.2,
            id = "scale_down")

        video_scale_up = AnimationList(
            transform = ("scale", [0.075, 0.095]),
            on_end = lambda c, g, u: c.animation_play(animation_to_play = "scale_down"),
            duration  = 0.2,
            id = "scale_up")

        video_scale_down = AnimationList(
            transform = ("scale", [0.07, 0.09]),
            duration  = 0.2,
            id = "scale_down")

        #### Grab animations

        main_position_down = AnimationList(
            transform = ("position", [0.03, demo_buttons_position]),
            duration  = 0.7*time_scale,
            id = "position_down")
        
        main_position_up = AnimationList(
            transform = ("position", [2.0, demo_buttons_position]),
            duration  = 0.7*time_scale,
            id = "position_up")

        video_position_down = AnimationList(
            transform = ("position", [0.78, demo_buttons_position]),
            duration  = 0.7*time_scale,
            id = "position_down")

        video_position_up = AnimationList(
            transform = ("position", [2.0, demo_buttons_position]),
            duration  = 0.7*time_scale,
            id = "position_up")

        time_scale*= 0.9

        button_main = Button(
            position   = [2.0, demo_buttons_position],
            offset = [0.0, 0.015*aspect_ratio],
            scale  = [0.25, 0.09],
            depth  = 0.83,
            colour     = vicos_red,
            animations = {main_scale_up.id: main_scale_up, main_scale_down.id: main_scale_down,
                          main_position_down.id: main_position_down, main_position_up.id: main_position_up},
            id = i)

        button_video = Button(
            position   = [2.0, demo_buttons_position],
            offset = [0.0, 0.015*aspect_ratio],
            scale  = [0.07, 0.09],
            depth  = 0.83,
            colour     = vicos_red,
            animations = {video_scale_up.id: video_scale_up, video_scale_down.id: video_scale_down,
                          video_position_down.id: video_position_down, video_position_up.id: video_position_up},
            id = i)

        button_text = TextField(
            position = [0.05, demo_buttons_position],
            offset   = [0.0, -0.022],
            text_scale = 0.7,
            depth  = 0.82,
            colour = [1.0, 1.0, 1.0, 0.75],
            aspect_ratio = aspect_ratio, 
            id = "demo_button_text_{}".format(i))
        button_text.set_text(font = font, text = demos[i]["cfg"]["highlight"])
        button_text.center_y()

        button_text.depends_on(element = button_main)
        video_icon_texture.depends_on(element = button_video)
        video_icon_texture.center_x()
        video_icon_texture.center_y()

        demo_buttons_position += 0.1
        demo_buttons.append(button_main)
        demo_video_buttons.append(button_video)

    parameters = Parameters(
        font   = font,
        aspect = aspect_ratio,
        state  = application_state)

    def on_click_video_button(button: Button, gui: Gui, state: State):

        video_key = button.id
        button.animation_play(animation_to_play = "scale_up")

        if display_screen.active_video is None:
            display_screen.insert_active_video(active_video = demo_video_scene(aspect_ratio, demo_videos[video_key], play_icon, pause_icon), active_video_button = button)

            button.set_colour(colour = vicos_gray)
        else:
            if button.mouse_click_count % 2 == 0:
                display_screen.remove_active_video()

                button.set_colour(colour = vicos_red)
            else:
                display_screen.active_video_button.mouse_click_count += 1
                display_screen.active_video_button.set_colour(colour = vicos_red)

                display_screen.insert_active_video(active_video = demo_video_scene(aspect_ratio, demo_videos[video_key], play_icon, pause_icon), active_video_button = button)

                button.set_colour(colour = vicos_gray)

    def on_click_demo_button(button: Button, gui: Gui, custom_data: State):
        
        demo_key = button.id
        button.animation_play(animation_to_play = "scale_up")

        if display_screen.active_demo is None:

            display_screen.insert_active_demo(active_demo = demo_scene_wrapper(aspect_ratio, demos[demo_key]["get_scene"](parameters)), active_demo_button = button)

            docker_command = "{} {}".format(1, demos[demo_key]["cfg"]["dockerId"])
            custom_data.echolib_handler.append_command((custom_data.echolib_handler.docker_publisher, docker_command))

            button.set_colour(colour = vicos_gray)
            vicos_intro_texture.animation_play(animation_to_play = "fade_out")
        else:
            if button.mouse_click_count % 2 == 0:

                display_screen.remove_active_demo()

                docker_command = "{} {}".format(-1, demos[demo_key]["cfg"]["dockerId"])
                custom_data.echolib_handler.append_command((custom_data.echolib_handler.docker_publisher, docker_command))

                button.set_colour(colour = vicos_red)
                vicos_intro_texture.animation_play(animation_to_play = "fade_in")
            else:

                display_screen.active_demo_button.mouse_click_count += 1
                display_screen.active_demo_button.set_colour(colour = vicos_red)

                docker_command = "{} {}".format(-1, demos[display_screen.active_demo_button.id]["cfg"]["dockerId"])
                custom_data.echolib_handler.append_command((custom_data.echolib_handler.docker_publisher, docker_command))

                docker_command = "{} {}".format(1, demos[demo_key]["cfg"]["dockerId"])
                custom_data.echolib_handler.append_command((custom_data.echolib_handler.docker_publisher, docker_command))

                display_screen.insert_active_demo(active_demo = demo_scene_wrapper(aspect_ratio, demos[demo_key]["get_scene"](parameters)), active_demo_button = button)

                button.set_colour(colour = vicos_gray)

        custom_data.echolib_handler.docker_channel_ready = False # Reset image return after demo is switched or terminated

    for b in demo_buttons:
        b.on_click = on_click_demo_button
        b.depends_on(element = drawer_menu_container)

    for b in demo_video_buttons:
        b.on_click = on_click_video_button
        b.depends_on(element = drawer_menu_container)

    #### Set some drawer menu behaviour

    def on_close(element, gui):

        if display_screen.active_video is None and display_screen.active_demo is None:
            hint.position[0] = 0.94
            hint.animation_play(animation_to_play = "fade_in")

        for b in demo_buttons:
            b.animation_stop(animation_to_stop = "position_down")
            b.animation_play(animation_to_play = "position_up")
        for b in demo_video_buttons:
            b.animation_stop(animation_to_stop = "position_down")
            b.animation_play(animation_to_play = "position_up")

    def on_grab(element, gui):

        for b in demo_buttons:
            b.animation_stop(animation_to_stop = "position_up")
            b.animation_play(animation_to_play = "position_down")
        for b in demo_video_buttons:
            b.animation_stop(animation_to_stop = "position_up")
            b.animation_play(animation_to_play = "position_down")

        hint.animation_play(animation_to_play = "fade_out")

    drawer_menu.on_grab  = on_grab
    drawer_menu.on_close = on_close

    return display_screen

def main():

    print("Starting VICOS DEMO OpenGL")

    config      = open("./cfg", "r")
    configLines = config.readlines()
    for line in configLines:

        tokens = line.split()

        t0 = tokens[0].lower()
        t1 = tokens[1]

        if t0 == "width":
            WIDTH = int(t1)
        elif t0 == "height":
            HEIGHT = int(t1)
        elif t0 == "fullscreen":
            FULLSCREEN = t1.lower() == "yes"

    #######################################################

    application_state = State()

    gui = Gui(fullscreen = FULLSCREEN, width = WIDTH, height = HEIGHT)

    font = load_font(path = "./res/fonts/Metropolis-SemiBold.otf")

    scene = scene_primary(gui.width, gui.height, application_state, font)
    scene.update_geometry(parent = None)

    while not gui.should_window_close():

        gui.poll_events()
        gui.clear_screen()

        scene.execute(parent = None, gui = gui, custom_data = application_state)
        
        gui.swap_buffers()

        # Resets camera image so no unecessary re-renders are done
        application_state.echolib_handler.set_camera_to_none()

        if gui.should_window_resize():

            scene = scene_primary(gui.width, gui.height, application_state, font)
            scene.update_geometry(parent = None)

    application_state.echolib_handler.running = False
    application_state.echolib_handler.handler_thread.join()

    glUseProgram(0)
    glfw.terminate()

if __name__ == "__main__":
    main()
