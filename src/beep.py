import subprocess

command = "paplay ../sounds/mario/nsmb_pipe.wav"

output = subprocess.check_output(command, shell=True)

print(output.decode())  

