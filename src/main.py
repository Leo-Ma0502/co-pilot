import argparse
import logging
import pathlib
import time

import picamera

from .led import Led
from .camera_capturer import CameraCapturer
from .camera_recorder import CameraRecorder
from .pubsub import PubSub
from .camera_info import CameraInfo
from .copilot import CoPilot
from .image_saver import AsyncImageSaver
from .blackbox import BlackBox


def parse_arguments():
    parser = argparse.ArgumentParser()
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
    return parser.parse_args()


def main():
    args = parse_arguments()
    args.blackbox_path = pathlib.Path(args.blackbox_path).joinpath(
        time.strftime("%Y%m%d-%H%M%S")
    )
    args.blackbox_path.mkdir(parents=True, exist_ok=True)

    log_path = args.blackbox_path.joinpath("co-pilot.log")
    logging.basicConfig(filename=str(log_path), level=logging.DEBUG)

    camera_info = CameraInfo("config/intrinsics.yml")
    pubsub = PubSub()
    image_saver = AsyncImageSaver(args.blackbox_path)

    blackbox = BlackBox(image_saver)

    with picamera.PiCamera() as camera:
        # fps for recording
        camera.framerate = 20
        camera.vflip = True
        camera.resolution = camera_info.resolution
        camera.exposure_mode = "sports"

        led_pin = 10
        led = Led(led_pin)
        camera_recorder = CameraRecorder(camera, led, args.blackbox_path)
        camera_capturer = CameraCapturer(
            camera, 5, camera_recorder.is_recording, pubsub
        )
        copilot = CoPilot(args, pubsub, blackbox, camera_info, led)
        copilot.run()


if __name__ == "__main__":
    main()
