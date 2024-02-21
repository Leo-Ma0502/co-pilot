# if in docker env
# python3 -m pip install --upgrade --extra-index-url https://google-coral.github.io/py-repo/ pycoral
xvfb-run -s "-screen 0 640x480x16" python3\
 -m src.reprocess\
  --ssd_model models/ssd_mobilenet_v2_coco_quant_no_nms_edgetpu.tflite \
  --label models/coco_labels.txt \
  --score_threshold 0.3 \
  --traffic_light_classification_model models/traffic_light_edgetpu.tflite \
  --traffic_light_label models/traffic_light_labels.txt \
  --blackbox_path=./ \
  --video tests/test_videos/dashcam/MOVI0495.mov \
  --fps 5