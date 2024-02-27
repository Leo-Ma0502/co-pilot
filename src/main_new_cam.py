import logging
import time
import argparse
import pathlib

from videoio import VideoReader
from PIL import Image

from .inference_config import InferenceConfig
from .copilot import CoPilot
from .pubsub import PubSub
from .camera_info import CameraInfo
from .whitebox import WhiteBox
from .image_saver import AsyncImageSaver
from .abc import ILed
from .beep import play_sound
from .beep import init_sound
# from .speaker import Speaker

import cv2
import os
import subprocess
import numpy as np
import datetime
import shutil

import threading
import queue




def stop_subprocess(proc):
    if proc.poll() is None:  
        proc.terminate()  
        time.sleep(0.001)  


def recreate_fifo_file(fifo_path):
    if os.path.exists(fifo_path):
        os.remove(fifo_path)  
    with open(fifo_path, 'wb'):
        pass 

def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--mode",
        help="select 'full' (full alert mode) or 'minimal' (yellow alert)",
        default='minimal'
    )

    parser.add_argument(
        "--lang",
        help="co-pilot voice language",
        default="en",
    )
    parser.add_argument(
        "--blackbox_path",
        help="Output path for blackbox (images, detections, video)",
        default="/mnt/hdd",
    )
    parser.add_argument(
        "--ssd_model",
        required=True,
        help="Detection SSD model path (must have post-processing operator).",
    )
    parser.add_argument(
        "--traffic_light_classification_model",
        required=True,
        help="Traffic Light Classification model path",
    )
    parser.add_argument("--label", help="Labels file path for SSD model.")
    parser.add_argument(
        "--traffic_light_label", help="Labels file path for traffic light model."
    )

    parser.add_argument(
        "--score_threshold",
        help="Threshold for returning the candidates.",
        type=float,
        default=0.1,
    )
    parser.add_argument(
        "--traffic_light_classification_threshold",
        help="Threshold for classify as traffic light",
        type=float,
        default=0.5,
    )
    parser.add_argument(
        "--iou_threshold",
        help=("threshold to merge bounding box duing nms"),
        type=float,
        default=0.1,
    )

    parser.add_argument(
        "--fps",
        help=("frame rate to play the video"),
        type=int,
        default=None,
    )

    parser.add_argument(
        "--video",
        help="path to the video to be reprocessed",
    )

    parser.add_argument(
        "--images",
        help="path to the folder of images to be reprocessed",
    )

    parser.add_argument(
        "--flip",
        action="store_true",
        help="flip top bottom of the video",
    )
    parser.add_argument(
        "--real_time",
        action="store_true",
        help="use real time reprocessing",
    )
    parser.add_argument(
        "--step",
        action="store_true",
        help="only step the frame when any key press",
    )
    parser.add_argument(
        "--cpu",
        action="store_true",
        help="use cpu or instead of tpu (default)",
    )
    return parser.parse_args()

def get_images(image_queue):
    print("producer thread starting.......")

    images_folder = "captured_images"
    if not os.path.exists(images_folder):
        os.makedirs(images_folder)
    else:
        shutil.rmtree(images_folder)
        os.makedirs(images_folder)

    fifo_path = 'video.h264'

    recreate_fifo_file(fifo_path)
    cmd = ['libcamera-vid', '-o', fifo_path, '--inline', '--width', '1920', '--height', '1080', '-t', '0', '--rotation', '180']
    proc = subprocess.Popen(cmd)


    fifo_fd = os.open(fifo_path, os.O_RDONLY | os.O_NONBLOCK)

    frame_data = b''
    count = 0
    data_read = 0
    start_point = 0

    subprocess.run(['sudo', 'rm', '*.h264'])
    print(f"cleared cache at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    while True:
        try:
            os.lseek(fifo_fd, start_point, os.SEEK_SET)
            print(f"---\n data read: {data_read}; start: {start_point} \n---")

            frame_data += os.read(fifo_fd, 1920 * 1080 * 3 * (count+1) - len(frame_data))
        

            data_read = len(frame_data)
            temp_file_path = f"temp_frame_{count}.h264"
            with open(temp_file_path, 'wb') as temp_file:
                temp_file.write(frame_data[:data_read] if start_point==0 else frame_data[start_point-1:data_read])

            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            saved_output = f"{images_folder}/image_{count}_{str(current_time)}.jpg"
            cmd = ['ffmpeg', '-y', '-i', temp_file_path, '-f', 'image2', '-vcodec', 'mjpeg', '-vframes', '1',
                        saved_output]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                

            os.remove(temp_file_path)

        
            start_point = data_read


            print(f"=============\n Have captured {count} images at {current_time}\n =============")

            image_queue.put(saved_output) 

            count += 1
        
        except ValueError as e:
            print(str(e))
            stop_subprocess(proc) 
            os.remove(temp_file_path)
            os.remove(fifo_path)
            break

        if cv2.waitKey(1) & 0xFF == ord('q'):
            stop_subprocess(proc) 
            os.remove(temp_file_path)
            os.remove(fifo_path)
            break
    image_queue.put(None)
    # copilot.stop()
       
def get_lights(copilot, inference_config, image_queue):
    print("consumer thread starting.......")
    while True:
        file_path = image_queue.get()

        if file_path is not None:
            print(f"-----------------\n start processing image \n -----------------")
            if os.path.exists(file_path):
                file = Image.open(file_path)
                inference_w, inference_h = inference_config.inference_resolution
                box = (0, 0, file.size[0], min(file.size[0] * inference_h / inference_w, file.size[1]))
                file = file.resize(inference_config.inference_resolution, box=box)
                copilot.process(file)
            else:
                print(f"file not found")
        else:
            print(f"-----------------\n no more images... \n -----------------")
            break




def main():
    init_sound()
    args = parse_arguments()
    args.blackbox_path = pathlib.Path(args.blackbox_path).joinpath(
        time.strftime("%Y%m%d-%H%M%S")
    )
    args.blackbox_path.mkdir(parents=True, exist_ok=True)
    log_path = args.blackbox_path.joinpath("co-pilot.log")
    logging.basicConfig(filename=str(log_path), level=logging.DEBUG)


    if args.cpu:
        from tflite_runtime.interpreter import Interpreter as make_interpreter
    else:
        from pycoral.utils.edgetpu import make_interpreter

    pubsub = PubSub()
    camera_info = CameraInfo("config/intrinsics.yml")
    inference_config = InferenceConfig("config/inference_config.yml")
    image_saver = AsyncImageSaver(args.blackbox_path)
    whitebox = WhiteBox(image_saver, args.step)

    try:
        copilot = CoPilot(
            args,
            pubsub,
            whitebox,
            camera_info,
            inference_config,
            ILed(),
            # Speaker(args.lang),
            make_interpreter(args.ssd_model),
            make_interpreter(args.traffic_light_classification_model),
        )
    except ValueError as e:
        print(str(e) + "Use --cpu if you do not have a coral tpu")
        return

    image_queue = queue.Queue()

    thread_producer = threading.Thread(target=get_images, args=(image_queue,))
    thread_consumer = threading.Thread(target=get_lights, args=(copilot, inference_config, image_queue))

    thread_producer.start()
    thread_consumer.start()

    thread_producer.join()
    thread_consumer.join()
   


if __name__ == "__main__":
    main()
