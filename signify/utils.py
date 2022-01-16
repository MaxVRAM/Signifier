
#    _________.__          ____ ___   __  .__.__          
#   /   _____/|__| ____   |    |   \_/  |_|__|  |   ______
#   \_____  \ |  |/ ___\  |    |   /\   __\  |  |  /  ___/
#   /        \|  / /_/  > |    |  /  |  | |  |  |__\___ \ 
#  /_______  /|__\___  /  |______/   |__| |__|____/____  >
#          \/   /_____/                                \/ 

def plural(value) -> str:
    """Return "s" or "" pluralise strings based on supplied (int) value or len(!int)."""
    if value is None:
        return ""
    try:
        num = int(value)
    except TypeError:
        num = len(value)
    except:
        return ""
    return "" if num == 1 else "s"