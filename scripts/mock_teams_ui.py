import tkinter as tk
import sys
import os

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
        print(f"Key pressed: {event.keysym}")
        if event.keysym in ('m', 'M', 'XF86AudioMute'):
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
