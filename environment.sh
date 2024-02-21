echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
sudo curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
sudo apt-get update
sudo apt install -y python3-opencv
sudo apt-get update 
sudo apt-get install -y xvfb
sudo apt-get install -y libedgetpu1-std
python3 -m pip install --no-cache-dir matplotlib videoio 
# sudo apt-get install -y python3-pycoral
# sudo apt-get install -y python3-tflite-runtime
# sudo python3 -m
pip install -r requirements_pi.txt
sudo apt-get install libsdl2-mixer-2.0-0  libsdl2-2.0-0


# instal ffmpeg
cd ~ 
sudo rm -rf x264
sudo rm -rf ffmpeg
git clone --depth 1 https://code.videolan.org/videolan/x264
cd x264
./configure --host=arm-unknown-linux-gnueabi --enable-static --disable-opencl
make -j4 && sudo make install
cd ~ && git clone git://source.ffmpeg.org/ffmpeg --depth=1
./configure --extra-ldflags="-latomic" --arch=armel --target-os=linux --enable-gpl --enable-omx --enable-omx-rpi --enable-nonfree
make -j4 && sudo make install