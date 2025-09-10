import datetime
import os

def get_shift_folder():
    """
    Tentukan folder shift berdasarkan jam sekarang.
    Shift 1: 07:00 - 15:00
    Shift 2: 15:00 - 23:00
    Shift 3: 23:00 - 07:00
    """
    now = datetime.datetime.now().time()

    if now >= datetime.time(7, 0) and now < datetime.time(15, 0):
        shift = "shift_1"
    elif now >= datetime.time(15, 0) and now < datetime.time(23, 0):
        shift = "shift_2"
    else:
        shift = "shift_3"

    folder = os.path.join("outputs", shift)
    os.makedirs(folder, exist_ok=True)
    return folder
