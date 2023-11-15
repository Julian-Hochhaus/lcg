import cv2
import tkinter as tk
from PIL import Image, ImageTk
import threading
import queue
from tkinter import ttk
import toml
RES_OPTIONS = {
    "640x480": (640, 480),
    "1920x1080": (1920, 1080),
    "2048x2048": (2048, 2048),
    "3072x2048": (3072, 2048)
}
def list_available_cameras():
    cameras = []
    index = 0
    while True and index < 10:
        cap = cv2.VideoCapture(index, cv2.CAP_V4L)
        if not cap.isOpened():
            cameras.append(f"Camera {index} is not available")
        else:
            cameras.append(f"Camera {index}")
            cap.release()
        index += 1

    if not cameras:
        print("No Cameras Available")
    else:
        print("Available Cameras:")
        for camera in cameras:
            print(camera)
    return cameras

class CameraApp:
    def __init__(self, root, camera_index, camera_list):
        self.root = root
        self.root.title("Camera GUI")

        self.video_label = tk.Label(root)
        self.video_label.pack()

        self.available_cameras=camera_list
        self.initial_camera_index = camera_index  # Store initial camera index
        self.cap = cv2.VideoCapture(camera_index)
        self.q = queue.Queue()
        self.stop_event = threading.Event()

        self.video_thread = threading.Thread(target=self.video_capture_thread)
        self.video_thread.daemon = True
        self.video_thread.start()

        self.settings_button = tk.Button(root, text="Open Settings", command=self.open_settings)
        self.settings_button.pack()
        self.resolutions = self.load_resolutions()
        self.stream_status_label = tk.Label(root, text="Stream Status: Stopped", fg="red")
        self.stream_status_label.pack()

        self.frame_width_label = tk.Label(root, text="Frame Width: ")
        self.frame_width_label.pack()

        self.frame_height_label = tk.Label(root, text="Frame Height: ")
        self.frame_height_label.pack()

        self.frame_rate_label = tk.Label(root, text="Frame Rate: ")
        self.frame_rate_label.pack()
        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

    def load_settings(self):
        try:
            with open('ccd_config.toml', 'r') as config_file:
                config = toml.load(config_file)
                self.initial_camera_index = config.get('initial_camera_index')
                self.selected_resolution.set(config.get('initial_resolution'))
        except FileNotFoundError:
            print('Error')
            self.initial_camera_index = 0
            self.selected_resolution.set("640x480")
        self.update_settings()
    def load_resolutions(self):
        resolutions = {}
        try:
            with open('ccd_config.toml', 'r') as config_file:
                config = toml.load(config_file)
                resolutions = config.get('resolutions', {})
        except FileNotFoundError:
            print('Error loading resolutions')

        return resolutions
    def save_settings(self):
        config = {
            "initial_camera_index": self.initial_camera_index,
            "initial_resolution": self.selected_resolution.get()
        }
        with open('ccd_config.toml', 'w') as config_file:
            toml.dump(config, config_file)

    def video_capture_thread(self):
        while not self.stop_event.is_set():
            ret, frame = self.cap.read()
            if ret:
                frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                frame_rate = self.cap.get(cv2.CAP_PROP_FPS)

                self.frame_width_label.config(text=f"Frame Width: {frame_width}")
                self.frame_height_label.config(text=f"Frame Height: {frame_height}")
                self.frame_rate_label.config(text=f"Frame Rate: {frame_rate:.2f}")
                self.stream_status_label.config(text="Stream Status: Running", fg="green")
            else:
                break

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)

            # Get the actual camera stream resolution
            actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            # Calculate the ratio to maintain a minimum height of 480 pixels
            ratio = float(actual_width/ actual_height)
            new_width = int(480* ratio)
            new_height = int(480)

            # Resize the frame while maintaining the aspect ratio
            resized_frame = img.resize((new_width, new_height), Image.ANTIALIAS)
            img = ImageTk.PhotoImage(resized_frame)

            try:
                self.q.put(img, block=False)
            except queue.Full:
                pass

        self.q.put(None)  # Signal the end of the video capture


    def update_video(self):
        try:
            img = self.q.get_nowait()
            if img is not None:
                self.video_label.imgtk = img
                self.video_label.configure(image=img)
                self.video_label.image = img  # Keep a reference
        except queue.Empty:
            pass

        self.root.after(10, self.update_video)

    def close_app(self):
        self.stop_event.set()
        if self.cap.isOpened():
            self.cap.release()
        self.root.destroy()

    def open_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        self.selected_resolution = tk.StringVar()
        self.selected_resolution.set("640x480")

        tk.Label(settings_window, text="Select Resolution:").pack()
        resolution_combobox = ttk.Combobox(settings_window, textvariable=self.selected_resolution,
                                           values=list(self.resolutions.keys()), state="readonly")
        resolution_combobox.pack()
        tk.Label(settings_window, text="Select Camera:").pack()
        camera_combobox = ttk.Combobox(settings_window, values=self.available_cameras, state="readonly")
        camera_combobox.current(self.initial_camera_index)
        camera_combobox.pack()

        update_button = tk.Button(settings_window, text="Update camera", command=self.update_settings)
        update_button.pack()

        save_button = tk.Button(settings_window, text="Save Settings to config", command=self.save_settings)
        save_button.pack()

        load_standard_button = tk.Button(settings_window, text="Load Settings from config", command=self.load_settings)
        load_standard_button.pack()

        camera_combobox.bind("<<ComboboxSelected>>", lambda event, cb=camera_combobox: self.change_camera(cb))

    def change_camera(self, camera_combobox):
        new_camera_index = camera_combobox.current()
        if new_camera_index != self.initial_camera_index:
            self.initial_camera_index = new_camera_index
            self.update_settings()  # Apply the new camera settings
    def update_settings(self):
        selected_resolution = self.selected_resolution.get()
        selected_width, selected_height = RES_OPTIONS[selected_resolution]

        try:

            if self.cap.isOpened():
                self.cap.release()
            self.cap = cv2.VideoCapture(self.initial_camera_index)  # Use initial camera index
            ret, frame = self.cap.read()
            if ret:
                frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                frame_rate = self.cap.get(cv2.CAP_PROP_FPS)

                self.frame_width_label.config(text=f"Frame Width: {frame_width}")
                self.frame_height_label.config(text=f"Frame Height: {frame_height}")
                self.frame_rate_label.config(text=f"Frame Rate: {frame_rate:.2f}")
                self.stream_status_label.config(text="Stream Status: Running", fg="green")
            else:
                # If the stream is stopped
                self.stream_status_label.config(text="Stream Status: Stopped", fg="red")
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, selected_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, selected_height)

            # Restart video thread with updated camera settings
            self.stop_event.set()
            self.video_thread.join()
            self.q = queue.Queue()
            self.stop_event.clear()
            self.video_thread = threading.Thread(target=self.video_capture_thread)
            self.video_thread.daemon = True
            self.video_thread.start()

        except ValueError:
            print("Please enter valid integers for width and height.")


def main():
    try:
        cameras = list_available_cameras()
        camera_index = int(input("Enter the camera index to use: "))

        if camera_index < len(cameras):
            root = tk.Tk()
            app = CameraApp(root, camera_index, cameras)
            app.update_video()  # Start the video update loop
            root.mainloop()
        else:
            print("Selected camera index is not available.")
    except ValueError:
        print("Please enter a valid camera index (an integer).")

if __name__ == "__main__":
    main()
