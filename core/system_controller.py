import pyautogui
import numpy as np
from core.utils import get_volume_interface

class SystemController:
    def __init__(self):
        self.w_scr, self.h_scr = pyautogui.size()
        self.vol_interface = get_volume_interface()
        
        # Smoothing for mouse
        self.ploc_x, self.ploc_y = 0, 0
        self.cloc_x, self.cloc_y = 0, 0
        self.smooth_factor = 5
        
        # State for drag and drop
        self.is_dragging = False

    def move_mouse(self, data):
        if not data: return
        cx, cy = data['center']
        w_cam, h_cam = 640, 480 # Default
        
        # Map with boundaries (100px margin)
        x3 = np.interp(cx, [100, w_cam-100], [0, self.w_scr])
        y3 = np.interp(cy, [100, h_cam-100], [0, self.h_scr])
        
        # Smoothen values
        self.cloc_x = self.ploc_x + (x3 - self.ploc_x) / self.smooth_factor
        self.cloc_y = self.ploc_y + (y3 - self.ploc_y) / self.smooth_factor
        
        pyautogui.moveTo(self.cloc_x, self.cloc_y)
        self.ploc_x, self.ploc_y = self.cloc_x, self.cloc_y

    def click(self, data=None):
        pyautogui.click()

    def right_click(self, data=None):
        pyautogui.rightClick()

    def start_drag(self, data=None):
        if not self.is_dragging:
            pyautogui.mouseDown()
            self.is_dragging = True

    def end_drag(self, data=None):
        if self.is_dragging:
            pyautogui.mouseUp()
            self.is_dragging = False

    def scroll(self, data):
        # lm[8] is index tip, lm[12] is middle tip
        # Use vertical distance between them or movement
        if 'lm' in data:
            dy = data['lm'][8][2] - data['lm'][12][2]
            pyautogui.scroll(int(dy * 2))

    def change_volume(self, data):
        if not self.vol_interface or 'lm' not in data: return
        lm = data['lm']
        # Distance between thumb and index
        dist = np.linalg.norm(np.array([lm[4][1], lm[4][2]]) - np.array([lm[8][1], lm[8][2]]))
        vol = np.interp(dist, [20, 200], [-65, 0])
        self.vol_interface.SetMasterVolumeLevel(vol, None)

    def press_key(self, key):
        pyautogui.press(key)
