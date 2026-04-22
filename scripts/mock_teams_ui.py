import tkinter as tk
import sys
import os
from logger_config import setup_logger

logger = setup_logger(__name__)

class MockTeamsUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Mock Teams UI")
        self.root.geometry("300x200+0+0") # Force position

        self.is_muted = False

        self.label = tk.Label(root, text="UNMUTE", font=("Helvetica", 48), bg="white")
        self.label.pack(expand=True, fill="both")

        # Bind keys to toggle mute
        self.root.bind('<Key>', self.on_key)

        # Keep window on top
        self.root.attributes('-topmost', True)
        self.root.focus_force()

    def on_key(self, event):
        # Support 'm', XF86AudioMute, and Ctrl+Shift+M (standard Teams shortcut)
        # In Tkinter, Ctrl+Shift+M can come as 'M' with specific state
        is_ctrl = (event.state & 0x4) != 0
        is_shift = (event.state & 0x1) != 0

        print(f"Key pressed: {event.keysym}, state: {event.state}")

        if event.keysym in ('m', 'M', 'XF86AudioMute'):
            if event.keysym in ('m', 'M') and is_ctrl and is_shift:
                logger.info("Detected Ctrl+Shift+M shortcut")
                self.toggle_mute()
            elif event.keysym == 'XF86AudioMute' or (event.keysym.lower() == 'm' and not is_ctrl):
                self.toggle_mute()

    def toggle_mute(self, event=None):
        self.is_muted = not self.is_muted
        if self.is_muted:
            self.label.config(text="MUTE", bg="red")
        else:
            self.label.config(text="UNMUTE", bg="white")
        print(f"Mute status changed: {'Muted' if self.is_muted else 'Unmuted'}")
        sys.stdout.flush()

if __name__ == "__main__":
    print("Starting Mock Teams UI...")
    sys.stdout.flush()
    root = tk.Tk()
    app = MockTeamsUI(root)
    print("Mock Teams UI ready. Press 'm' to toggle.")
    sys.stdout.flush()
    root.mainloop()
