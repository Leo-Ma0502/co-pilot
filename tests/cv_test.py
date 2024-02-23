import cv2
import os
import subprocess
import numpy as np
import datetime
import time

images_folder = "captured_images"
if not os.path.exists(images_folder):
    os.makedirs(images_folder)

def stop_subprocess(proc):
    if proc.poll() is None:  
        proc.terminate()  
        time.sleep(0.001)  


def recreate_fifo_file(fifo_path):
    if os.path.exists(fifo_path):
        os.remove(fifo_path)  
    with open(fifo_path, 'wb'):
        pass 

fifo_path = 'video.h264'

recreate_fifo_file(fifo_path)
cmd = ['sudo', 'libcamera-vid', '-o', fifo_path, '--inline', '--width', '1920', '--height', '1080', '-t', '0']
proc = subprocess.Popen(cmd)


fifo_fd = os.open(fifo_path, os.O_RDONLY | os.O_NONBLOCK)

frame_data = b''
count = 0
data_read = 0
start_point = 0

try:
    while True:

        os.lseek(fifo_fd, start_point, os.SEEK_SET)
        print(f"---\n data read: {data_read}; start: {start_point} \n---")

        frame_data += os.read(fifo_fd, 1920 * 1080 * 3 * (count+1) - len(frame_data))
    

        data_read = len(frame_data)
        temp_file_path = f"temp_frame_{count}.h264"
        with open(temp_file_path, 'wb') as temp_file:
            temp_file.write(frame_data[:data_read] if start_point==0 else frame_data[start_point-1:data_read])

        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cmd = ['ffmpeg', '-y', '-i', temp_file_path, '-f', 'image2', '-vcodec', 'mjpeg', '-vframes', '1',
                    f"{images_folder}/image_{count}_{str(current_time)}.jpg"]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            

        os.remove(temp_file_path)

       
        start_point = data_read


        print(f"=============\n Have captured {count} images at {current_time}\n")
        count += 1

        if cv2.waitKey(1) & 0xFF == ord('q'):
            stop_subprocess(proc) 
            os.remove(temp_file_path)
            os.remove(fifo_path)
            break
        
finally:
    stop_subprocess(proc) 
    os.remove(fifo_path)
    os.close(fifo_fd)
    print(f"=============\n process cleared \n==============")
