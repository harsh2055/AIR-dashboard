"""
core/utils.py — Platform helpers for Aether Gesture Platform
"""
import platform


def get_volume_interface():
    """Returns a Windows IAudioEndpointVolume interface, or None on other platforms."""
    if platform.system() != 'Windows':
        return None
    try:
        import comtypes
        comtypes.CoInitialize()
        from pycaw.pycaw import AudioUtilities
        devices = AudioUtilities.GetSpeakers()
        return devices.EndpointVolume
    except Exception as e:
        print(f'[Aether] Audio init failed: {e}')
        return None


def get_platform():
    return platform.system()  # 'Windows', 'Darwin', 'Linux'


def is_windows():
    return platform.system() == 'Windows'
