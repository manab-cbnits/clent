import shutil


def separator():
    width = shutil.get_terminal_size((120, 20)).columns
    if width <= 0:
        width = 120
    print("=" * width)