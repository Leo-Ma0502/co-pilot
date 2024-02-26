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
# from .speaker import Speaker

import queue
import threading


def get_image_gen(args, inference_config):
    if args.video:
        default_fps = 20
        for i, frame in enumerate(VideoReader(args.video)):
            if args.fps and i % (default_fps // args.fps) != 0:
                continue

            image = Image.fromarray(frame)
            if args.flip:
                image = image.transpose(method=Image.FLIP_TOP_BOTTOM)

            inference_w, inference_h = inference_config.inference_resolution
            box = (0, 0, image.size[0], min(image.size[0] * inference_h / inference_w, image.size[1]))
            image = image.resize(inference_config.inference_resolution, box=box)
            yield image

    if args.images:
        path_to_test_images = pathlib.Path(args.images)
        image_paths = sorted(list(path_to_test_images.glob("*.jpg")))
        for image_path in image_paths:
            image = Image.open(image_path, "r").convert("RGB")
            inference_w, inference_h = inference_config.inference_resolution
            box = (0, 0, image.size[0], min(image.size[0] * inference_h / inference_w, image.size[1]))
            image = image.resize(inference_config.inference_resolution, box=box)
            yield image

    # if args.queue:
    #     while True:
    #         image_path = image_queue.get()
    #         if image_path is None:
    #             break
            
    #         print(f"Processing {image_path}")
    #         try:
    #             image = Image.open(image_path, "r").convert("RGB")
    #             inference_w, inference_h = inference_config.inference_resolution
    #             box = (0, 0, image.size[0], min(image.size[0] * inference_h / inference_w, image.size[1]))
    #             image = image.resize(inference_config.inference_resolution, box=box)
    #             yield image
    #         except Exception as e:
    #             print(f"Error processing image {image_path}: {e}")
            
    #         os.remove(image_path)  
            
    #         image_queue.task_done()  

    else:
        assert "must provide --video or --images"


def reprocess(args):
    # print("=== start reprocessing ===")
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

    for image in get_image_gen(args, inference_config):
        # print("=== processing images ===")
        copilot.process(image)
        # if args.real_time:
        #    time.sleep(0.05)
    copilot.stop()


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

    # parser.add_argument(
    #     "--queue",
    #     help="get image from queue",
    # )

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


def main():
    args = parse_arguments()
    args.blackbox_path = pathlib.Path(args.blackbox_path).joinpath(
        time.strftime("%Y%m%d-%H%M%S")
    )
    args.blackbox_path.mkdir(parents=True, exist_ok=True)
    log_path = args.blackbox_path.joinpath("co-pilot.log")
    logging.basicConfig(filename=str(log_path), level=logging.DEBUG)
    reprocess(args)


if __name__ == "__main__":
    main()
