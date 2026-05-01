import pyautogui
import numpy as np
import os
import platform

# Only initialize Windows specific audio modules if on Windows
if platform.system() == "Windows":
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# Disable pyautogui fail-safe exception for edge cases
pyautogui.FAILSAFE = False

class SystemController:
    def __init__(self):
        self.volume_interface = None
        self.min_vol = 0
        self.max_vol = 0
        
        # Setup Volume Interface for Windows
        if platform.system() == "Windows":
            try:
                import comtypes
                comtypes.CoInitialize()
                devices = AudioUtilities.GetSpeakers()
                self.volume_interface = devices.EndpointVolume
                vol_range = self.volume_interface.GetVolumeRange()
                self.min_vol = vol_range[0]
                self.max_vol = vol_range[1]
            except Exception as e:
                print("Could not initialize audio:", e)

    def set_volume(self, length, min_len=30, max_len=200):
        """Map pinch distance to system volume level."""
        if not self.volume_interface:
            return 0, 0

        # Interpolate length to volume range
        vol = np.interp(length, [min_len, max_len], [self.min_vol, self.max_vol])
        # Interpolate length to UI bar and percentage
        vol_bar = np.interp(length, [min_len, max_len], [400, 150])
        vol_per = np.interp(length, [min_len, max_len], [0, 100])
        
        # Set the volume
        self.volume_interface.SetMasterVolumeLevel(vol, None)
        return vol_bar, vol_per

    def move_mouse(self, x, y, w_cam, h_cam, w_scr, h_scr, smooth_x, smooth_y, smoothening=5):
        """Moves the mouse with smoothing logic."""
        # Convert coordinates to screen size
        x_mapped = np.interp(x, [100, w_cam - 100], [0, w_scr])
        y_mapped = np.interp(y, [100, h_cam - 100], [0, h_scr])

        # Smoothen the movement
        smooth_x = smooth_x + (x_mapped - smooth_x) / smoothening
        smooth_y = smooth_y + (y_mapped - smooth_y) / smoothening
        
        # Move mouse (mirror the x-axis for natural movement)
        try:
            pyautogui.moveTo(w_scr - smooth_x, smooth_y)
        except Exception:
            pass
            
        return smooth_x, smooth_y

    def click_mouse(self):
        """Executes a single click."""
        pyautogui.click()
