import cv2
import tkinter as tk
from PIL import Image, ImageTk
import threading
import queue
import numpy as np
from tkinter import ttk
import toml
import os
from socket import *
import subprocess
import tkinter.filedialog as filedialog
script_directory = os.path.dirname(os.path.abspath(__file__))
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
        self.root.geometry("1300x900")
        self.root.maxsize(width=1300, height=900)
        self.videoframes=tk.Frame(root, borderwidth=5, height=490, width=1290)
        self.videoframes.pack(side='top')
        self.video_label = tk.Label(self.videoframes, text="Livefeed")
        self.video_label.pack(side="left")
        self.last_saved_image_label = tk.Label(self.videoframes, text="Last Saved Image")
        self.last_saved_image_label.pack(side="right")
        self.available_cameras = camera_list
        self.initial_camera_index = camera_index  # Store initial camera index

        self.set_gain_to_manual(self.initial_camera_index)
        current_gain_auto = self.get_gain_auto(self.initial_camera_index)
        if current_gain_auto == 0:
            print("gain set to manual mode")
        else:
            print("gain is not in manual mode, please check/adapt with terminal or TCam")
        self.cap = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"FFV1"))
        print("format",self.cap.get(cv2.CAP_PROP_FOURCC))
        self.q = queue.Queue()
        self.stop_event = threading.Event()

        self.video_thread = threading.Thread(target=self.video_capture_thread)
        self.video_thread.daemon = True
        self.video_thread.start()

        self.bottom_frame = tk.Frame(root, borderwidth=5)
        self.bottom_frame.pack(side='bottom')
        self.settings_frame = tk.Frame(self.bottom_frame, borderwidth=5)
        self.settings_frame.pack(side='left')
        self.info_frame = tk.Frame(self.bottom_frame, borderwidth=5)
        self.info_frame.pack(side='right')
        self.settings_button = tk.Button(self.settings_frame, text="Open Settings", command=self.open_settings)
        self.settings_button.pack()
        self.resolutions = self.load_resolutions()
        self.brightness = 200
        self.gain = 0
        self.auto_exposure=3
        self.boolean_auto_exposure=True
        self.stream_status_label = tk.Label(self.info_frame, text="Stream Status: Stopped", fg="red")
        self.stream_status_label.pack(side="bottom")

        self.frame_width_label = tk.Label(self.info_frame, text="Frame Width: ")
        self.frame_width_label.pack()

        self.frame_height_label = tk.Label(self.info_frame, text="Frame Height: ")
        self.frame_height_label.pack()

        self.frame_rate_label = tk.Label(self.info_frame, text="Frame Rate: ")
        self.frame_rate_label.pack()
        self.capture_button = tk.Button(self.settings_frame, text="Capture Single Photo", command=self.capture_photo)
        self.capture_button.pack()
        self.device_label = tk.Label(self.settings_frame, text="Device Control:")
        self.device_label.pack()

        self.command_label = tk.Label(self.settings_frame, text="Command:")
        self.command_label.pack()

        self.command_entry = tk.Entry(self.settings_frame)
        self.command_entry.pack()

        self.result_label = tk.Label(self.settings_frame, text="Result:")
        self.result_label.pack()

        self.send_command_button = tk.Button(self.settings_frame, text="Send Command", command=self.send_command)
        self.send_command_button.pack()

        self.select_directory_button = tk.Button(self.settings_frame, text="Select Save Directory", command=self.select_directory)
        self.select_directory_button.pack()

        # Create a button to start the image capture loop
        self.start_capture_button = tk.Button(self.settings_frame, text="Start Image Capture Loop",
                                              command=lambda: self.capture_images_loop())  # Example energy values
        self.start_capture_button.pack()

        # Socket configuration for the second device
        self.server_host = '129.217.168.64'
        self.server_port = 4004
        self.device_socket = socket(AF_INET, SOCK_STREAM)
        self.device_socket.connect((self.server_host, self.server_port))


        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

    def display_last_saved_image(self, frame):
        # Update the label to display the last saved image
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame)

        # Get the actual camera stream resolution
        actual_width = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_height = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        # Calculate the ratio to maintain a minimum height of 480 pixels
        ratio = float(actual_width / actual_height)
        new_width = int(480 * ratio)
        new_height = int(480)

        # Resize the frame while maintaining the aspect ratio
        resized_frame = img.resize((new_width, new_height), Image.ANTIALIAS)
        img = ImageTk.PhotoImage(resized_frame)
        self.last_saved_image_label.config(image=img)
        self.last_saved_image_label.image = img  # Keep a reference to prevent garbage collection

    def capture_images_loop(self, start_energy=10, end_energy=100, increment=9):
        self.select_directory()
        self.capture_energy_image(start_energy, end_energy, increment)

    def capture_energy_image(self, energy, end_energy, increment):
        if energy <= end_energy:
            def capture_next():
                self.capture_energy_image(energy + increment, end_energy, increment)

            command = f'VEN{float(energy)}\r'
            # Send the command to the device
            self.device_socket.send(command.encode())
            data_set = self.device_socket.recv(256)
            self.device_socket.send('REN\r'.encode())
            data_read = self.device_socket.recv(256)
            print(data_read.decode('utf-8'))
            # Display the result in the result_label
            self.result_label.config(text=f"Result: {data_read.decode('utf-8')}")
            self.root.after(5000)
            # Capture image
            ret, frame = self.cap.read()
            if ret:
                file_path = self.save_directory + f'/images/EN_{energy}.jpg'
                # Save the captured frame as an image
                cv2.imwrite(file_path, frame)
                print(f"Photo captured and saved as '{file_path}'")
                self.display_last_saved_image(frame)
            else:
                print("Failed to capture photo")

            # Schedule the next capture after a delay (10 seconds)
            self.root.after(5000, capture_next)
        else:
            print("Image capturing completed")

    def select_directory(self):
        # Allow the user to select a directory for saving images
        self.save_directory = filedialog.askdirectory()
        print("Save directory:", self.save_directory)
    def send_command(self):
        energy = self.command_entry.get()
        command=f'VEN{float(energy)}\r'




        # Send the command to the device
        self.device_socket.send(command.encode())
        data_set = self.device_socket.recv(256)
        self.device_socket.send('REN\r'.encode())
        data_read = self.device_socket.recv(256)
        print(data_read.decode('utf-8'))
        # Display the result in the result_label
        self.result_label.config(text=f"Result: {data_read.decode('utf-8')}")
    def capture_photo(self):
        ret, frame = self.cap.read()
        if ret:
            file_path = filedialog.asksaveasfilename(defaultextension=".jpg",
                                                     filetypes=[("JPEG files", "*.jpg"), ("All files", "*.*")],
                                                     title="Save Photo As")
            if file_path:
                # Save the captured frame as an image with the user-specified filename and directory
                cv2.imwrite(file_path, frame)
                print(f"Photo captured and saved as '{file_path}'")
                self.display_last_saved_image(frame)
            else:
                print("Photo capturing canceled")
        else:
            print("Failed to capture photo")

    def load_settings(self):
        try:
            with open(script_directory+'/ccd_config.toml', 'r') as config_file:
                config = toml.load(config_file)
                self.initial_camera_index = config.get('CameraSettings', {}).get('initial_camera_index')
                self.selected_resolution.set(config.get('CameraSettings', {}).get('initial_resolution'))
                self.brightness = config.get('CameraSettings', {}).get('brightness')
                self.gain = config.get('CameraSettings', {}).get('gain')  # Adding gain to the settings

        except FileNotFoundError:
            print('Error')
            self.initial_camera_index = 0
            self.selected_resolution.set("640x480")
        self.update_settings()
    def load_resolutions(self):
        resolutions = {}
        try:
            with open(script_directory+'/ccd_config.toml', 'r') as config_file:
                config = toml.load(config_file)
                resolutions = config.get('CameraSettings', {}).get('resolutions')
                print(resolutions)
        except FileNotFoundError as e:
            print('Error: File not found:', e)
        except Exception as e:
            print('Error loading resolutions:', e)
        return resolutions
    def save_settings(self):
        # Read existing configuration
        with open(script_directory+'/ccd_config.toml', 'r') as config_file:
            config = toml.load(config_file)

        # Update specific settings
        config['CameraSettings']['initial_camera_index'] = self.initial_camera_index
        config['CameraSettings']['brightness'] = self.brightness
        config['CameraSettings']['gain'] = self.gain

        # Rewrite the updated settings back to the file
        with open(script_directory+'/ccd_config.toml', 'w') as config_file:
            toml.dump(config, config_file)

    def video_capture_thread(self):
        while not self.stop_event.is_set():
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
        tk.Label(settings_window, text="Brightness:").pack()
        brightness_scale = tk.Scale(settings_window, from_=0, to=4095, resolution=1, orient=tk.HORIZONTAL,
                                    command=self.set_brightness)
        brightness_scale.set(self.brightness)
        brightness_scale.pack()

        tk.Label(settings_window, text="Gain:").pack()
        gain_scale = tk.Scale(settings_window, from_=0, to=480, resolution=1, orient=tk.HORIZONTAL, command=self.set_gain)
        gain_scale.set(self.gain)
        gain_scale.pack()
        exposure_time_absolute = tk.Scale(settings_window, from_=0.1, to=50, resolution=0.1, orient=tk.HORIZONTAL,
                                          label="Exposure Time (s)", command=self.set_exposure_time_absolute)
        exposure_time_absolute.set(333)  # Set the default value
        exposure_time_absolute.pack()

        auto_exposure= tk.BooleanVar()
        auto_exposure.set(True)  # Set the default value for gain auto checkbox
        self.auto_exposure_checkbox = tk.Checkbutton(settings_window, text="Gain Auto", var=self.boolean_auto_exposure)
        self.auto_exposure_checkbox.pack()



        update_button = tk.Button(settings_window, text="Update camera", command=self.update_settings)
        update_button.pack()

        save_button = tk.Button(settings_window, text="Save Settings to config", command=self.save_settings)
        save_button.pack()

        load_standard_button = tk.Button(settings_window, text="Load Settings from config", command=self.load_settings)
        load_standard_button.pack()

        camera_combobox.bind("<<ComboboxSelected>>", lambda event, cb=camera_combobox: self.change_camera(cb))

    def set_brightness(self, value):
        self.brightness = float(value)

    def set_exposure_time_absolute(self, value):
        self.exposure_time_absolute= 10000*float(value)


    def set_gain(self, value):
        self.gain = float(value)

    # Function to set gain_auto using subprocess
    def set_gain_to_manual(self, camera_index):
        try:
            device='/dev/video'+str(camera_index)
            subprocess.run(['v4l2-ctl', '--device', device, '--set-ctrl=gain_auto=0'])
            print("gain_auto set to 0 successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error setting gain to manual: {e}")

    # Function to get gain_auto using subprocess
    def get_gain_auto(self, camera_index):
        try:
            device = '/dev/video' + str(camera_index)
            result = subprocess.run(['v4l2-ctl', '--device', device, '--get-ctrl=gain_auto'],
                                    capture_output=True, text=True)
            output = result.stdout.strip()
            return int(output.split(':')[1])
        except subprocess.CalledProcessError as e:
            print(f"Error getting gain_auto: {e}")
            return None

    def change_camera(self, camera_combobox):
        new_camera_index = camera_combobox.current()
        if new_camera_index != self.initial_camera_index:
            self.initial_camera_index = new_camera_index
            self.set_gain_to_manual(self.initial_camera_index)
            self.update_settings()  # Apply the new camera settings
    def update_settings(self):
        selected_resolution = self.selected_resolution.get()
        selected_width, selected_height = RES_OPTIONS[selected_resolution]
        try:

            if self.cap.isOpened():
                self.cap.release()
            self.set_gain_to_manual(self.initial_camera_index)
            current_gain_auto = self.get_gain_auto(self.initial_camera_index)
            if current_gain_auto == 0:
                print("gain in in manual mode")
            else:
                print("gain is not in manual mode, please check/adapt with terminal or TCam")
            self.cap = cv2.VideoCapture(self.initial_camera_index, cv2.CAP_V4L2)  # Use initial camera index
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

            self.cap.set(cv2.CAP_PROP_BRIGHTNESS, self.brightness)
            self.cap.set(cv2.CAP_PROP_GAIN, self.gain)
            self.cap.set(cv2.CAP_PROP_EXPOSURE, self.exposure_time_absolute)
            if not self.boolean_auto_exposure:
                self.auto_exposure = 1
            else:
                self.auto_exposure = 3
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)

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
