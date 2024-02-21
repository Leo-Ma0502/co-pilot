
# command = "paplay ../sounds/mario/nsmb_pipe.wav"

# output = subprocess.check_output(command, shell=True)

# print(output.decode())  


import subprocess

def play_sound(new_color, previous_color):
    """
    Play a sound file using the `paplay` command.

    Args:
        new_color (str): The color of the traffic light
        previous_color (str): The previous color of the traffic light

    Returns:
        None
    """
    print(f"Traffic light changed from {previous_color} to {new_color}")
    file_path = get_path(new_color)
    try:
        if(file_path!="invalid color"):
            subprocess.check_call(['paplay', file_path])
        else:
            print("invalid color")
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")


def get_path(color):
    """
    determine the sound track based on traffic color

    Args:
        color (str): The color of the traffic light

    Returns:
        path (str)
    """
    if isinstance(color, str):
        if "red" in color:
            return "./sounds/mario/smb_pause.wav"
        elif "yellow" in color:
            return "./sounds/mario/nsmb_pipe.wav"
        elif "green" in color:
            return "./sounds/mario/smb_1-up.wav"
        else:
            return "invalid color"
    else: 
        return "invalid color"
