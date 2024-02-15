import cv2
from camera_device import CameraDevice
from tkinter_new_dir import *
from leed_device import LEEDDevice
import tkinter as tk
from PIL import Image, ImageTk
import threading
import queue
import numpy as np
from tkinter import ttk
import toml
import os
import csv
from bisect import bisect_left
import subprocess
import tkinter.filedialog as filedialog
import json

script_directory = os.path.dirname(os.path.abspath(__file__))
settings_window = None
__version__ = "0.4.4"


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


class LCGApp():
    def __init__(self, root, camera_index, camera_list):
        self.approx_exposure = []
        self.approx_gain = []
        self.capture_step = 0
        self.root = root
        self.root.title(f"LCG: LEED Camera GUI v.{__version__}")
        self.root.geometry("1400x1020")
        self.root.maxsize(width=1920, height=1100)


        # self.last_saved_image_label.pack(side="right")
        # initialisation of all values
        self.available_cameras = camera_list
        self.camera_index = camera_index  # Store initial camera index
        self.resolutions = self.load_resolutions()
        self.selected_resolution = tk.StringVar()
        self.selected_resolution.set('640x480')
        self.brightness = 100
        self.gain = 100
        self.exposure_time = 0.5
        self.boolean_auto_exposure = tk.BooleanVar()
        self.auto_exposure_value = 1
        self.boolean_auto_gain = tk.BooleanVar()
        self.auto_gain_value = 0
        self.set_exposure_time_absolute(self.exposure_time)
        self.calibration_file = script_directory + '/calibrations/calibration.csv'

        self.set_auto_gain(self.camera_index, self.auto_gain_value)
        self.videoframes = tk.Canvas(root, width=1380, height=490)
        self.videoframes.pack(side='top')
        self.videoframes.update()
        # Place the live stream and last saved image on the Canvas
        self.video_label = tk.Label(self.videoframes, text="Livefeed")

        self.livefeed_window = self.videoframes.create_window(self.videoframes.winfo_width() // 4,
                                                              self.videoframes.winfo_height() / 2,
                                                              window=self.video_label, anchor=tk.CENTER)
        x1, y1, _, _ = self.videoframes.bbox(self.livefeed_window)
        self.videoframes.create_rectangle(x1 + self.video_label.winfo_reqwidth() // 2 - 320,
                                          y1 + self.video_label.winfo_reqheight() // 2 - 240,
                                          x1 + self.video_label.winfo_reqwidth() // 2 + 320,
                                          y1 + self.video_label.winfo_reqheight() // 2 + 240, fill="grey95",
                                          outline="black")
        self.last_saved_image_label = tk.Label(self.videoframes, text="Last Saved Image")
        self.last_saved_image_label_window = self.videoframes.create_window(self.videoframes.winfo_width() * 3 // 4,
                                                                            self.videoframes.winfo_height() / 2,
                                                                            window=self.last_saved_image_label,
                                                                            anchor=tk.CENTER)
        x2, y2, _, _ = self.videoframes.bbox(self.last_saved_image_label_window)
        self.videoframes.create_rectangle(x2 + self.last_saved_image_label.winfo_reqwidth() // 2 - 320,
                                          y2 + self.last_saved_image_label.winfo_reqheight() // 2 - 240,
                                          x2 + self.last_saved_image_label.winfo_reqwidth() // 2 + 320,
                                          y2 + self.last_saved_image_label.winfo_reqheight() // 2 + 240, fill="grey95",
                                          outline="black")

        self.camera = CameraDevice(self.camera_index)

        self.q = queue.Queue()
        self.stop_event = threading.Event()

        self.video_thread = threading.Thread(target=self.video_capture_thread)
        self.video_thread.daemon = True
        self.video_thread.start()

        label_font = ('Arial', 12)
        button_font = ('Arial', 12)

        # Bottom Frame
        self.bottom_frame = tk.Frame(root, borderwidth=5)
        self.bottom_frame.pack(side='bottom')

        # Settings Frame
        self.settings_frame = tk.Frame(self.bottom_frame, bd=2, relief=tk.RIDGE)
        self.settings_frame.pack()

        # Device Settings Frame
        self.device_settings_frame = tk.Frame(self.bottom_frame, bd=2, relief=tk.RIDGE)
        self.device_settings_frame.pack()

        # LEED Settings Frame
        self.leed_device_frame = tk.Frame(self.device_settings_frame, bd=2, relief=tk.RIDGE)
        self.leed_device_frame.pack(side='left')
        self.leed_info_frame = tk.Frame(self.leed_device_frame, bd=2, relief=tk.RIDGE)
        self.leed_info_frame.pack()
        self.leed_settings_frame = tk.Frame(self.leed_device_frame, bd=2, relief=tk.RIDGE)
        self.leed_settings_frame.pack()

        # Camera Settings Frame
        self.camera_settings_frame = tk.Frame(self.device_settings_frame, bd=2, relief=tk.RIDGE)
        self.camera_settings_frame.pack(side='left')

        # Info Frame
        self.info_frame = tk.Frame(self.device_settings_frame, bd=2, relief=tk.RIDGE)
        self.info_frame.pack(side="left")

        self.series_frame = tk.Frame(self.info_frame)
        self.series_frame.pack()
        self.series_label0 = tk.Label(self.series_frame, text="Status Series Capture:", font=("Courier", 12), width=50,
                                      height=1,
                                      anchor="nw")
        self.series_label0.pack()
        self.series_label = tk.Label(self.series_frame, text="Not running!", font=("Courier", 12), width=50, height=3,
                                     anchor="nw")
        self.series_label.pack()
        button_width = 25

        self.info_label = tk.Label(self.info_frame, text="Stream Info:", font=label_font, width=25)
        self.info_label.pack()
        self.stream_status_label = tk.Label(self.info_frame, text="Stream Status: Stopped", fg="red")
        self.stream_status_label.pack(side="top", pady=5)
        self.frame_width_label = tk.Label(self.info_frame, text="Frame Width: ", font=label_font)
        self.frame_width_label.pack()

        self.frame_height_label = tk.Label(self.info_frame, text="Frame Height: ", font=label_font)
        self.frame_height_label.pack()

        self.frame_rate_label = tk.Label(self.info_frame, text="Frame Rate: ", font=label_font)
        self.frame_rate_label.pack()
        self.leed_info_frame_label = tk.Label(self.leed_info_frame, text="LEED Info:", width=25, font=label_font)
        self.leed_info_frame_label.pack()
        self.screen_label = tk.Label(self.leed_info_frame, text="SCREEN state: N/A")
        self.screen_label.pack()
        self.beam_current_label = tk.Label(self.leed_info_frame, text="BEAM CURRENT: N/A")
        self.beam_current_label.pack()
        self.cathode_label = tk.Label(self.leed_info_frame, text="Cathode state: N/A")
        self.cathode_label.pack()
        self.device_label = tk.Label(self.leed_settings_frame, text="LEED Control:", width=25, font=label_font)
        self.device_label.pack()

        leed_test_frame = tk.Frame(self.leed_settings_frame)
        leed_test_frame.pack()
        leed_command_frame = tk.Frame(leed_test_frame)
        leed_command_frame.pack()
        self.command_label = tk.Label(leed_command_frame, text="Energy:", font=label_font)
        self.command_label.pack(side=tk.LEFT)

        self.command_entry = tk.Entry(leed_command_frame)
        self.command_entry.pack(side=tk.LEFT)

        self.set_energy_button = tk.Button(leed_command_frame, text="Set energy", command=self.set_energy,
                                           font=button_font)
        self.set_energy_button.pack(side=tk.LEFT)
        leed_test_output = tk.Frame(leed_test_frame)
        leed_test_output.pack()
        result_frame = tk.Frame(leed_test_output, bd=2, relief=tk.RAISED, bg="grey65")
        result_frame.pack()

        self.result_label_terminal = tk.Label(result_frame, text="LEED Device Output", bg="grey70", fg="black",
                                              font=("Courier", 12, 'bold'), width=50,
                                              height=1, anchor="nw")
        self.result_label_terminal.pack(side=tk.TOP)

        output_frame = tk.Frame(result_frame, bd=2, relief=tk.SUNKEN, bg="black")
        output_frame.pack()

        self.result_label = tk.Label(output_frame, text=">", bg="grey40", fg="white", font=("Courier", 12), width=50,
                                     height=5, anchor="nw")
        self.result_label.pack()

        self.info_cam_label = tk.Label(self.camera_settings_frame, text="Camera control:", font=label_font, width=25)
        self.info_cam_label.pack()

        # Buttons with fixed widths and font settings
        self.settings_button = tk.Button(self.settings_frame, text="Open Settings", command=self.open_settings,
                                         width=button_width, font=button_font)
        self.settings_button.pack()

        self.capture_button = tk.Button(self.camera_settings_frame, text="Capture Single Photo",
                                        command=self.capture_photo, width=button_width, font=button_font)
        self.capture_button.pack()

        frame_save_directory = tk.Frame(self.camera_settings_frame)
        frame_save_directory.pack()
        self.current_save_directory = tk.Label(frame_save_directory, text="Save Directory:")
        self.current_save_directory.pack(side=tk.LEFT)
        self.save_directory =self.set_save_directory()
        self.save_directory_text = tk.Text(frame_save_directory, wrap=tk.WORD, height=1, width=25)
        self.save_directory_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.save_directory_text.insert(tk.END, self.save_directory)
        self.save_directory_text.pack(side=tk.LEFT)
        self.save_directory_text.bind("<FocusOut>", self.check_directory)
        self.select_directory_button = tk.Button(self.camera_settings_frame, text="Select Save Directory",
                                                 command=self.select_directory, width=button_width, font=button_font)
        self.select_directory_button.pack()
        frame_series = tk.Frame(self.camera_settings_frame, bd=2, relief=tk.RIDGE)
        frame_series.pack()
        label_series = tk.Label(frame_series, text='Settings Series:')
        label_series.pack()
        image_series_frame = tk.Frame(frame_series)
        image_series_frame.pack()
        image_series_subframe1 = tk.Frame(frame_series)
        image_series_subframe1.pack()
        image_series_subframe2 = tk.Frame(frame_series)
        image_series_subframe2.pack()
        image_series_subframe3 = tk.Frame(frame_series)
        image_series_subframe3.pack()
        self.confirm_settings_button = tk.Button(frame_series, text="Confirm Settings", command=self.confirm_settings,
                                                 width=button_width, font=button_font)
        self.confirm_settings_button.pack()
        self.label_series_confirm = tk.Label(frame_series, text='Series will be recorded with:\n', bg='grey95',
                                             fg='black', height=5, anchor='nw')
        self.label_series_confirm.pack()
        start_energy_label = tk.Label(image_series_subframe1, text="Start Energy (eV):", font=label_font)
        start_energy_label.pack(side=tk.LEFT)
        self.start_energy_valid = tk.Label(image_series_subframe1, text="Invalid", fg="red")
        self.start_energy_valid.pack(side=tk.RIGHT)
        self.start_energy_entry = tk.Entry(image_series_subframe1)
        self.start_energy_entry.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        end_energy_label = tk.Label(image_series_subframe2, text=" End Energy (eV):", font=label_font)
        end_energy_label.pack(side=tk.LEFT)
        self.end_energy_valid = tk.Label(image_series_subframe2, text="Invalid", fg="red")
        self.end_energy_valid.pack(side=tk.RIGHT)
        self.end_energy_entry = tk.Entry(image_series_subframe2)
        self.end_energy_entry.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        step_energy_label = tk.Label(image_series_subframe3, text="Energy Step (eV):", font=label_font)
        step_energy_label.pack(side=tk.LEFT)

        self.step_energy_valid = tk.Label(image_series_subframe3, text="Invalid", fg="red")
        self.step_energy_valid.pack(side=tk.RIGHT)
        self.step_energy_entry = tk.Entry(image_series_subframe3)
        self.step_energy_entry.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        frame_calibration_file = tk.Frame(frame_series)
        frame_calibration_file.pack()
        self.current_calibration_file = tk.Label(frame_calibration_file, text="Calibration File:")
        self.current_calibration_file.pack(side=tk.LEFT)

        self.calibration_file_text = tk.Text(frame_calibration_file, wrap=tk.WORD, height=1, width=25)
        self.calibration_file_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.calibration_file_text.insert(tk.END, self.calibration_file)
        self.calibration_file_text.bind("<FocusOut>", self.check_file_exists)
        self.boolean_use_calibration_file = tk.BooleanVar()
        self.boolean_use_calibration_file.set(False)
        self.boolean_use_calibration_checkbox = tk.Checkbutton(frame_calibration_file, text="Use calibration file",
                                                               var=self.boolean_use_calibration_file)
        self.boolean_use_calibration_checkbox.pack()
        self.select_calibration_file_button = tk.Button(frame_series, text="Select Calibration File",
                                                        command=self.choose_calibration_file)
        self.select_calibration_file_button.pack()
        self.start_energy_entry.bind("<FocusOut>", self.validate_start_energy)
        self.end_energy_entry.bind("<FocusOut>", self.validate_end_energy)
        self.step_energy_entry.bind("<FocusOut>", self.validate_step_energy)

        self.start_capture_button = tk.Button(self.camera_settings_frame, text="Start Image Capture Loop",
                                              command=lambda: self.capture_images_loop(), width=button_width,
                                              font=button_font)
        self.start_capture_button.pack()
        self.initialize_settings_frame()
        self.load_camera_settings()
        self.update_settings()
        # Socket configuration for the LEED
        self.leed_device = LEEDDevice(leed_host='129.217.168.64', leed_port=4004)
        self.load_leed_settings()
        self.update_leed_states()

        self.root.protocol("WM_DELETE_WINDOW", self.close_app)


    def update_leed_states(self):
        def read_screen():
            screen_state, screen_result = self.leed_device.read_screen()
            if screen_state:
                self.screen_label.config(text=f"SCREEN state: ON: {float(screen_result) / 1000}kV", fg="green",
                                         font=("Arial", 12))
            else:
                self.screen_label.config(text=f"SCREEN state: OFF", fg="red", font=("Arial", 12))

        def read_cathode():
            cathode_state, cathode_result = self.leed_device.read_cathode()
            if cathode_state:
                self.cathode_label.config(text=f"Cathode state: ON: {float(cathode_result)}A", fg="green",
                                          font=("Arial", 12))
            else:
                self.cathode_label.config(text=f"Cathode state: OFF", fg="red", font=("Arial", 12))

        def read_beam_current():
            beam_current_state, beam_current = self.leed_device.read_beam_current()
            if beam_current_state:
                self.beam_current_label.config(text=f"Beam current: {float(beam_current)}A", fg="green",
                                               font=("Arial", 12))
            else:
                self.beam_current_label.config(text=f"Beam Current: Not available", fg="red", font=("Arial", 12))

        # Schedule function calls with delays
        self.root.after(500, read_screen)
        self.root.after(1000, read_cathode)
        self.root.after(1500, read_beam_current)
        self.root.after(2000, lambda: None)

    def check_file_exists(self, event):
        if event.widget == self.calibration_file_text:
            new_file_path = self.calibration_file_text.get("1.0", "end-1c").strip()
        if event.widget == self.calibration_file_text_config:
            new_file_path = self.calibration_file_text_config.get("1.0", "end-1c").strip()
        if os.path.isfile(new_file_path):
            self.calibration_file = new_file_path
            self.calibration_file_text.delete(1.0, tk.END)
            self.calibration_file_text_config.delete(1.0, tk.END)
            self.calibration_file_text.insert(tk.END, self.calibration_file)
            self.calibration_file_text_config.insert(tk.END, self.calibration_file)
            print("Calibration file successfully set to:", self.calibration_file)
        else:
            print("File does not exist. Reverting to last saved one.")
            self.calibration_file_text.delete(1.0, tk.END)
            self.calibration_file_text_config.delete(1.0, tk.END)
            self.calibration_file_text.insert(tk.END, self.calibration_file)
            self.calibration_file_text_config.insert(tk.END, self.calibration_file)

    def check_directory(self, event):
        new_directory = self.save_directory_text.get("1.0", "end-1c")
        if os.path.isdir(new_directory):
            self.save_directory = new_directory
            print("Save directory set to:", self.save_directory)
        else:
            print("Invalid directory. Reverting to last saved one.")
            self.save_directory_text.delete("1.0", tk.END)
            self.save_directory_text.insert(tk.END, self.save_directory)

    def confirm_settings(self):
        if self.start_energy_valid.cget('text') == 'Valid' and self.end_energy_valid.cget(
                'text') == 'Valid' and self.step_energy_valid.cget('text') == 'Valid':
            start = float(self.start_energy_entry.get())
            end = float(self.end_energy_entry.get())
            step = float(self.step_energy_entry.get())
            length = (end - start) // step + 1
            text = f'LEED Series will be recorded in:\n {length} steps @{step} eV\n from {start} eV to {end} eV.\n To' \
                   f' start the Series Capture, press:\n \'Start Image Capture Loop\' '

        else:
            text = 'Please check, that all given energy values are valid floats!'
        self.label_series_confirm.config(text=text)

    def validate_start_energy(self, event):
        new_value = self.start_energy_entry.get()
        if self.is_float(new_value):
            self.start_energy_valid.config(text="Valid", fg="green")
        else:
            self.start_energy_valid.config(text="Invalid", fg="red")

    def validate_end_energy(self, event):
        new_value = self.end_energy_entry.get()
        if self.is_float(new_value):
            self.end_energy_valid.config(text="Valid", fg="green")
        else:
            self.end_energy_valid.config(text="Invalid", fg="red")

    def validate_step_energy(self, event):
        new_value = self.step_energy_entry.get()
        if self.is_float(new_value):
            self.step_energy_valid.config(text="Valid", fg="green")
        else:
            self.step_energy_valid.config(text="Invalid", fg="red")

    @staticmethod
    def is_float(value):
        try:
            float(value)
            return True
        except ValueError:
            return False

    def display_last_saved_image(self, frame):
        # Update the label to display the last saved image
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame)

        # Get the actual camera stream resolution
        actual_width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
        # Calculate the ratio to maintain a minimum height of 480 pixels
        ratio = float(actual_width / actual_height)
        new_width = int(480 * ratio)
        new_height = int(480)

        # Resize the frame while maintaining the aspect ratio
        resized_frame = img.resize((new_width, new_height), Image.ANTIALIAS)
        img = ImageTk.PhotoImage(resized_frame)
        self.last_saved_image_label.config(image=img)
        self.last_saved_image_label.image = img  # Keep a reference to prevent garbage collection

    def capture_images_loop(self):
        self.select_directory()
        if self.start_energy_valid.cget('text') == 'Valid' and self.end_energy_valid.cget(
                'text') == 'Valid' and self.step_energy_valid.cget('text') == 'Valid':
            start = float(self.start_energy_entry.get())
            end = float(self.end_energy_entry.get())
            step = float(self.step_energy_entry.get())
            length = (end - start) // step + 1
            text = f'LEED Series started with:\n {length} steps @{step} eV\n from {start} eV to {end} eV.\n'

        else:
            start = 10
            end = 100
            step = 5
            length = (end - start) // step + 1
            text = f'Not all given energies are valid floats!\n Series started with standard values:\n {length} steps' \
                   f' @{step} eV\n from {start} eV to {end} eV.\n '
        self.label_series_confirm.config(text=text)
        self.capture_step = 0
        self.approx_gain, self.approx_exposure = self.precalculate_gain_and_exposure(start, end, length)
        self.capture_energy_image(start, end, step)

    def lin_interpolate(self, x, x_list, y_list):
        i = bisect_left(x_list, x)
        if i == 0:
            return y_list[0]
        elif i == len(x_list):
            return y_list[-1]
        else:
            x0, x1 = x_list[i - 1], x_list[i]
            y0, y1 = y_list[i - 1], y_list[i]
            return y0 + (y1 - y0) * ((x - x0) / (x1 - x0))

    def precalculate_gain_and_exposure(self, start, end, length):
        energy_values = []
        gain_values = []
        exposure_values = []
        print(self.calibration_file)
        with open(self.calibration_file, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                energy_values.append(float(row['Energy (eV)']))
                gain_values.append(float(row['Gain']))
                exposure_values.append(float(row['Exposure (s)']))
        sorted_indexes=np.asarray(energy_values).argsort()
        energy_values=np.asarray(energy_values)[sorted_indexes]
        gain_values=np.asarray(gain_values)[sorted_indexes]
        exposure_values=np.asarray(exposure_values)[sorted_indexes]
        min_energy = start
        max_energy = end
        num_points = int(length)

        approximation_gain_array = []
        approximation_exposure_array = []
        for i in range(num_points):
            energy = min_energy + ((max_energy - min_energy) / num_points) * i
            gain = int(self.lin_interpolate(energy, energy_values, gain_values))
            exposure = np.round(self.lin_interpolate(energy, energy_values, exposure_values), 1)
            approximation_gain_array.append(gain)
            approximation_exposure_array.append(exposure)
        return approximation_gain_array, approximation_exposure_array

    def capture_energy_image(self, energy, end_energy, step):
        if energy <= end_energy:

            def capture_next():
                self.capture_energy_image(energy + step, end_energy, step)

            #self.update_leed_states()
            self.leed_device.send_energy(energy)
            #self.result_label.config(text=f"Result: {self.leed_device.read_energy()[-1]}")
            #self.output_leed.config(text=f"Result: {self.leed_device.read_energy()[-1]}")
            self.camera.set(cv2.CAP_PROP_EXPOSURE, self.approx_exposure[self.capture_step] * 10000)
            self.camera.set(cv2.CAP_PROP_GAIN, self.approx_gain[self.capture_step])
            break_time = 1000 if self.camera.get(cv2.CAP_PROP_EXPOSURE) // 10 < 1000 else self.camera.get(
                cv2.CAP_PROP_EXPOSURE) // 10
            self.root.after(int(5 * break_time))  # short break depending on camera exposure time (at least 5sec!)
            status, frame = self.camera.get_frame()
            if status:
                file_path = self.save_directory + f'/EN_{energy}.png'
                # Save the captured frame as a PNG image in 16-bit format
                cv2.imwrite(file_path, frame, [cv2.IMWRITE_PNG_COMPRESSION, 16])
                print(f"Photo captured and saved as '{file_path}'")
                #self.display_last_saved_image(frame)
            else:
                print("Failed to capture photo")
            self.capture_step += 1
            self.root.after(int(3 * break_time), capture_next)
        else:
            print("Image capturing completed")

    def select_calibration_file(self):
        new_file_path = filedialog.asksaveasfilename()

        if new_file_path:
            if not os.path.isfile(new_file_path):
                try:
                    with open(new_file_path, 'w') as new_file:
                        # Create an empty file if it doesn't exist
                        pass
                    print(f"New file created at: {new_file_path}")
                except OSError as e:
                    print(f"Failed to create file: {e}")
            else:
                print("File already exists.")

            self.calibration_file = new_file_path
            self.update_calibration_file_text()

    def choose_calibration_file(self):
        file_path = filedialog.askopenfilename()

        if file_path:
            if not os.path.isfile(file_path):
                print(f"Calibration file: {file_path} does not exist.")
            else:
                self.calibration_file = file_path
                self.update_calibration_file_text()

    def update_calibration_file_text(self):
        # Update text boxes with the calibration file path
        self.calibration_file_text.delete(1.0, tk.END)
        self.calibration_file_text_config.delete(1.0, tk.END)
        self.calibration_file_text.insert(tk.END, self.calibration_file)
        self.calibration_file_text_config.insert(tk.END, self.calibration_file)
        print("Calibration file successfully set to:", self.calibration_file)

    def select_directory(self):
        # self.save_directory = filedialog.askdirectory()
        dialog = CustomFolderDialog(save_directory=self.save_directory)
        dialog.title("Select/Create New Folder")
        dialog.wait_window()
        if dialog.new_folder_path.get():  # If folder path is not empty
            self.save_directory = dialog.new_folder_path.get()
        self.save_directory_text.delete(1.0, tk.END)  # Clear existing text
        self.save_directory_text.insert(tk.END, self.save_directory)
        print("Save directory:", self.save_directory)

    def set_save_directory(self):
        with open('config.toml', 'r') as f:
            config = toml.load(f)
        if 'save_directory' in config and 'path' in config['save_directory']:
            return config['save_directory']['path']
        else:
             # Set default save_directory to the directory of lcg
             save_directory = os.path.dirname(os.path.abspath(__file__)) # get script_directory
        return save_directory


    def set_energy(self):
        energy = self.command_entry.get()
        try:
            energy_float = float(energy)
            self.update_leed_states()
            result = self.leed_device.send_energy(energy_float)
            self.result_label.config(text=f"{result}")
            self.output_leed.config(text=f"{result}")
        except ValueError:
            self.result_label.config(text="Invalid energy value. Please enter a valid number.")
            self.output_leed.config(text="Invalid energy value. Please enter a valid number.")

    def set_energy_leed(self):
        energy = self.command_energy_entry.get()
        try:
            energy_float = float(energy)
            self.update_leed_states()
            result = self.leed_device.send_energy(energy_float)
            self.result_label.config(text=f"{result}")
            self.output_leed.config(text=f"{result}")
        except ValueError:
            self.result_label.config(text="Invalid energy value. Please enter a valid number.")
            self.output_leed.config(text="Invalid energy value. Please enter a valid number.")

    def capture_photo(self):
        status, frame = self.camera.get_frame()
        if status:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".jpg",
                initialdir=self.save_directory,
                filetypes=[
                    ("JPEG files", "*.jpg"),
                    ("PNG files", "*.png"),
                    ("TIFF files", "*.tiff"),
                    ("All files", "*.*")
                ],
                title="Save Photo As"
            )
            if file_path:
                file_extension = file_path.split('.')[-1].lower()

                if file_extension == 'png':
                    # Save as PNG with 16-bit depth
                    cv2.imwrite(file_path, frame, [cv2.IMWRITE_PNG_COMPRESSION, 16])
                elif file_extension == 'tiff':
                    # Save as TIFF with 16-bit depth
                    cv2.imwrite(file_path, frame, [cv2.IMWRITE_TIFF_XDPI, 300, cv2.IMWRITE_TIFF_YDPI, 300])
                else:
                    # Default: Save as JPEG (8-bit depth)
                    cv2.imwrite(file_path, frame)

                print(f"Photo captured and saved as '{file_path}'")
                self.display_last_saved_image(frame)
            else:
                print("Photo capturing canceled")
        else:
            print("Failed to capture photo")

    def load_camera_settings(self):
        try:
            with open(script_directory + '/config.toml', 'r') as config_file:
                config = toml.load(config_file)
                self.camera_index = config.get('CameraSettings', {}).get('camera_index')
                self.selected_resolution.set(config.get('CameraSettings', {}).get('initial_resolution'))
                self.brightness = config.get('CameraSettings', {}).get('brightness')
                self.gain = config.get('CameraSettings', {}).get('gain')
                self.auto_gain_value = 0 if not config.get('CameraSettings', {}).get('gain_auto') else 1
                self.boolean_auto_gain.set(True) if config.get('CameraSettings', {}).get(
                    'gain_auto') else self.boolean_auto_gain.set(False)
                self.auto_exposure_value = 1 if not config.get('CameraSettings', {}).get('exposure_auto') else 3
                self.boolean_auto_exposure.set(True) if config.get('CameraSettings', {}).get(
                    'exposure_auto') else self.boolean_auto_exposure.set(False)
                self.exposure_time = config.get('CameraSettings', {}).get('exposure_time')

        except FileNotFoundError:
            print('Settings File not found.')
            self.camera_index = 0
            self.selected_resolution.set("640x480")
            self.brightness = 100
            self.gain = 100
            self.auto_gain_value = 0
            self.auto_exposure_value = 1
            self.exposure_time = 1
        self.update_settings_camera_ui()

    def load_resolutions(self):
        resolutions = {}
        try:
            with open(script_directory + '/config.toml', 'r') as config_file:
                config = toml.load(config_file)
                resolutions = config.get('CameraSettings', {}).get('resolutions')
        except FileNotFoundError as e:
            print('Error: File not found:', e)
        except Exception as e:
            print('Error loading resolutions:', e)
        return resolutions

    def save_camera_settings(self):
        # Read existing configuration
        with open(script_directory + '/config.toml', 'r') as config_file:
            config = toml.load(config_file)

        # Update specific settings
        config['CameraSettings']['camera_index'] = self.camera_index
        config['CameraSettings']['initial_resolution'] = self.selected_resolution.get()
        config['CameraSettings']['brightness'] = self.brightness
        config['CameraSettings']['gain'] = self.gain
        config['CameraSettings']['gain_auto'] = self.boolean_auto_gain.get()
        config['CameraSettings']['exposure_time'] = self.exposure_time
        config['CameraSettings']['exposure_auto'] = self.boolean_auto_exposure.get()
        # Rewrite the updated settings back to the file
        with open(script_directory + '/config.toml', 'w') as config_file:
            toml.dump(config, config_file)

    def load_leed_settings(self):
        try:
            with open(script_directory + '/config.toml', 'r') as config_file:
                config = toml.load(config_file)
                host = config.get('LEEDSettings', {}).get('server_host')
                port = config.get('LEEDSettings', {}).get('server_port')
        except FileNotFoundError:
            host = "129.217.168.64"
            port = 4004
        self.leed_server_host_text.set(host)
        self.leed_server_port_text.set(port)

    def save_leed_settings(self):
        with open(script_directory + '/config.toml', 'r') as config_file:
            config = toml.load(config_file)
        if self.leed_device.validate_leed_ip(self.leed_server_host_text.get()):
            config['LEEDSettings']['server_host'] = self.leed_server_host_text.get()
            config['LEEDSettings']['server_port'] = self.leed_server_port_text.get()
        else:
            print('Current configuration does not contain a valid IP, therefore it was not saved.')
        with open(script_directory + '/config.toml', 'w') as config_file:
            toml.dump(config, config_file)

    def video_capture_thread(self):
        while not self.stop_event.is_set():
            status, frame = self.camera.get_frame()
            if status:
                frame_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
                frame_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
                frame_rate = self.camera.get(cv2.CAP_PROP_FPS)

                self.frame_width_label.config(text=f"Frame Width: {frame_width}")
                self.frame_height_label.config(text=f"Frame Height: {frame_height}")
                self.frame_rate_label.config(text=f"Frame Rate: {frame_rate:.2f}")
                self.stream_status_label.config(text="Stream Status: Running", fg="green")
            else:
                break

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)

            # Get the actual camera stream resolution
            actual_width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
            # Calculate the ratio to maintain a minimum height of 480 pixels
            ratio = float(actual_width / actual_height)
            new_width = int(480 * ratio)
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
        self.camera.close_camera()
        self.root.destroy()

    def open_settings(self):
        global settings_window
        if settings_window:
            settings_window.deiconify()
            settings_window.lift()
        else:
            self.initialize_settings_frame()

    def on_settings_window_close(self):
        global settings_window
        settings_window.withdraw()

    def on_settings_window_minimize(self, event):
        # not working on ubuntu
        global settings_window
        settings_window.withdraw()

    # Bind the method to the <Unmap> event of the settings window
    def initialize_settings_frame(self):
        global settings_window

        if settings_window:
            settings_window.lift()
            return

        settings_window = tk.Toplevel(self.root, bg='grey80', width=700)
        settings_window.title("Settings")
        settings_window.withdraw()

        settings_camera = tk.Frame(settings_window, bd=2, relief=tk.RIDGE, bg='grey85')
        settings_camera.pack(padx=10, pady=10)
        tk.Label(settings_camera, text="Camera Settings", font=('Arial', 12, 'bold')).pack()

        camera_frame = tk.Frame(settings_camera)
        camera_frame.pack()
        tk.Label(camera_frame, text="Select Camera:").pack()
        self.camera_combobox = ttk.Combobox(camera_frame, values=self.available_cameras, state="readonly")
        self.camera_combobox.current(self.camera_index)
        self.camera_combobox.pack()

        resolution_frame = tk.Frame(settings_camera)
        resolution_frame.pack()
        tk.Label(resolution_frame, text="Select Resolution:").pack()
        self.resolution_combobox = ttk.Combobox(resolution_frame, textvariable=self.selected_resolution,
                                                values=list(self.resolutions.keys()), state="readonly")
        if self.selected_resolution.get() in self.resolutions:
            self.resolution_combobox.set(self.selected_resolution.get())
        self.resolution_combobox.pack()

        brightness_frame = tk.Frame(settings_camera)
        brightness_frame.pack()
        tk.Label(brightness_frame, text="Brightness:").pack()
        self.brightness_scale = tk.Scale(brightness_frame, from_=0, to=4095, resolution=1, orient=tk.HORIZONTAL,
                                         command=self.set_brightness, length=410)
        self.brightness_scale.set(self.brightness)
        self.brightness_scale.pack()

        gain_frame = tk.Frame(settings_camera)
        gain_frame.pack()
        tk.Label(gain_frame, text="Gain:").pack()
        self.gain_scale = tk.Scale(gain_frame, from_=0, to=480, resolution=1, orient=tk.HORIZONTAL,
                                   command=self.set_gain, length=480)
        self.gain_scale.set(self.gain)
        self.gain_scale.pack()

        exposure_frame = tk.Frame(settings_camera)
        exposure_frame.pack()
        self.exposure_time_entry = tk.Scale(exposure_frame, from_=0.0, to=10, resolution=0.025, orient=tk.HORIZONTAL,
                                            label="Exposure Time (s)", length=400,
                                            command=self.set_exposure_time_absolute)
        self.exposure_time_entry.set(self.exposure_time)  # Set the default value
        self.exposure_time_entry.pack()

        auto_exposure_frame = tk.Frame(settings_camera)
        auto_exposure_frame.pack()
        self.boolean_auto_exposure = tk.BooleanVar()
        self.boolean_auto_exposure.set(True)
        self.auto_exposure_checkbox = tk.Checkbutton(auto_exposure_frame, text="Auto Exposure",
                                                     var=self.boolean_auto_exposure)
        self.auto_exposure_checkbox.pack()

        auto_gain_frame = tk.Frame(settings_camera)
        auto_gain_frame.pack()
        self.boolean_auto_gain.set(True)
        self.auto_gain_checkbox = tk.Checkbutton(auto_gain_frame, text="Auto Gain",
                                                 var=self.boolean_auto_gain)
        self.auto_gain_checkbox.pack()

        # Buttons
        button_frame = tk.Frame(settings_camera)
        button_frame.pack()
        update_button = tk.Button(button_frame, text="Update camera", command=self.update_settings)
        update_button.pack(side=tk.LEFT)

        save_button = tk.Button(button_frame, text="Save Camera Settings\n to config",
                                command=self.save_camera_settings)
        save_button.pack(side=tk.LEFT)

        load_standard_button = tk.Button(button_frame, text="Load Camera Settings\n from config",
                                         command=self.clicked_load_settings)
        load_standard_button.pack(side=tk.LEFT)

        self.camera_combobox.bind("<<ComboboxSelected>>", lambda event, cb=self.camera_combobox: self.change_camera(cb))

        leed_settings_frame = tk.Frame(settings_window, bd=2, relief=tk.RIDGE, bg='grey85')
        leed_settings_frame.pack()

        tk.Label(leed_settings_frame, text="LEED Settings", font=('Arial', 12, 'bold')).pack()

        server_host_frame = tk.Frame(leed_settings_frame)
        server_host_frame.pack()
        self.leed_server_host_text = tk.StringVar()

        tk.Label(server_host_frame, text="Server Host:").pack(side="left")
        self.leed_server_host_entry = tk.Entry(server_host_frame, textvariable=self.leed_server_host_text)
        self.leed_server_host_entry.pack(side="left")
        self.validity_label = tk.Label(server_host_frame, text="Invalid IP", fg="red", font=("Arial", 11))
        self.validity_label.pack(side="left")
        self.leed_server_port_text = tk.StringVar()

        tk.Label(leed_settings_frame, text="Server Port:").pack()
        self.leed_server_port_entry = tk.Entry(leed_settings_frame, textvariable=self.leed_server_port_text)
        self.leed_server_port_entry.pack()
        self.leed_server_host_entry.bind("<FocusOut>", self.validate_leed_ip)
        self.leed_server_port_text.trace("w", self.on_leed_server_port_change)

        leed_test_frame = tk.Frame(leed_settings_frame, bd=2, bg='grey85', highlightthickness=1,
                                   highlightbackground="black")
        leed_test_frame.pack()
        leed_energy_frame = tk.Frame(leed_test_frame)
        leed_energy_frame.pack()
        leed_energy_label = tk.Label(leed_energy_frame, text="Energy:")
        leed_energy_label.pack(side=tk.LEFT)

        self.command_energy_entry = tk.Entry(leed_energy_frame)
        self.command_energy_entry.pack(side=tk.LEFT)

        set_energy_button = tk.Button(leed_energy_frame, text="Set energy", command=self.set_energy_leed)
        set_energy_button.pack(side=tk.LEFT)
        leed_command_frame = tk.Frame(leed_test_frame)
        leed_command_frame.pack()
        label = tk.Label(leed_command_frame, text='Command:(Format: CMD)\n*don\'t include \\r!*')
        label.pack(side=tk.LEFT)

        self.entry_test_command = tk.Entry(leed_command_frame)
        self.entry_test_command.pack(side=tk.LEFT)

        test_command_button = tk.Button(leed_command_frame, text="Send command", command=self.send_cmd_leed)
        test_command_button.pack(side=tk.LEFT)
        leed_test_output = tk.Frame(leed_test_frame)
        leed_test_output.pack()
        result_frame = tk.Frame(leed_test_output, bd=2, relief=tk.RAISED, bg="grey65")
        result_frame.pack()

        self.result_label_config_terminal = tk.Label(result_frame, text="LEED Device Output", bg="grey70", fg="black",
                                                     font=("Courier", 12, 'bold'), width=50,
                                                     height=1, anchor="nw")
        self.result_label_config_terminal.pack(side=tk.TOP)

        output_frame = tk.Frame(result_frame, bd=2, relief=tk.SUNKEN, bg="black")
        output_frame.pack()

        self.output_leed = tk.Label(output_frame, text=">", bg="grey40", fg="white", font=("Courier", 12), width=50,
                                    height=5, anchor="nw")
        self.output_leed.pack()
        leed_button_frame = tk.Frame(leed_settings_frame)
        leed_button_frame.pack()
        leed_save_button = tk.Button(leed_button_frame, text="Save LEED Settings\n to config",
                                     command=self.save_leed_settings)
        leed_save_button.pack(side=tk.LEFT)
        load_leed_button = tk.Button(leed_button_frame, text="Load LEED Settings\n from config",
                                     command=self.load_leed_settings)
        load_leed_button.pack(side=tk.LEFT)
        settings_window.bind("<Unmap>", lambda event: self.on_settings_window_minimize(event))
        settings_window.protocol("WM_DELETE_WINDOW", lambda: self.on_settings_window_close())
        calibration_settings_frame = tk.Frame(settings_window, bd=2, relief=tk.RIDGE, bg='grey85')
        calibration_settings_frame.pack()
        tk.Label(calibration_settings_frame, text="Calibration Settings:", font=('Arial', 12, 'bold')).pack()
        self.output_calibration = tk.Text(calibration_settings_frame, bg="grey95", fg="grey20", font=("Courier", 11),
                                          width=50,
                                          height=5)
        self.output_calibration.pack()
        self.calibration_values = []

        frame_calibration_file_config = tk.Frame(calibration_settings_frame)
        frame_calibration_file_config.pack()
        current_calibration_file = tk.Label(frame_calibration_file_config, text="Calibration File:")
        current_calibration_file.pack(side=tk.LEFT)
        self.calibration_file_text_config = tk.Text(frame_calibration_file_config, wrap=tk.WORD, height=1, width=25)
        self.calibration_file_text_config.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.calibration_file_text_config.insert(tk.END, self.calibration_file)
        self.calibration_file_text_config.bind("<FocusOut>", self.check_file_exists)
        calibration_buttons_frame = tk.Frame(calibration_settings_frame)
        calibration_buttons_frame.pack()
        set_calibration_button = tk.Button(calibration_buttons_frame, text="Add Calibration\n datapoint",
                                           command=self.add_calibration_datapoint)
        set_calibration_button.pack(side=tk.LEFT)
        reset_calibration_button = tk.Button(calibration_buttons_frame, text="Reset temporary\n Calibration",
                                             command=self.reset_calibration_values)
        reset_calibration_button.pack(side=tk.LEFT)
        save_calibration_button = tk.Button(calibration_buttons_frame, text="Save calibration\n to file",
                                            command=self.save_calibration_values)
        save_calibration_button.pack(side=tk.LEFT)

    def add_calibration_datapoint(self):
        self.update_leed_states()
        energy = self.leed_device.read_energy()[-1]
        if energy is None:
            print("Failed to retrieve a valid energy value. Please try again.")
            return
        gain = self.camera.get(cv2.CAP_PROP_GAIN)
        exposure_time_in_s = self.camera.get(cv2.CAP_PROP_EXPOSURE) // 10000
        for index, entry in enumerate(self.calibration_values):
            if entry[0] == energy:
                self.calibration_values[index] = (energy, gain, exposure_time_in_s)
                break
        else:
            self.calibration_values.append((energy, gain, exposure_time_in_s))

        self.calibration_values = sorted(self.calibration_values, key=lambda x: x[0])

        self.output_calibration.delete("1.0", "end")
        for entry in self.calibration_values:
            self.output_calibration.insert("end", f"{entry}\n")

    def reset_calibration_values(self):
        self.calibration_values = []
        self.output_calibration.delete("1.0", "end")

    def save_calibration_values(self):
        self.select_calibration_file()
        filename = self.calibration_file
        with open(filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Energy (eV)', 'Gain', 'Exposure (s)'])
            writer.writerows(self.calibration_values)
        print(f'Calibration saved to:{self.calibration_file}')
        self.output_calibration.delete("1.0", "end")
        self.output_calibration.insert('end',
                                       f'Calibration saved to:{self.calibration_file}\n Temporary calibration still '
                                       f'available! Current values:')
        for entry in self.calibration_values:
            self.output_calibration.insert("end", f"{entry}\n")

    def send_cmd_leed(self):
        cmd = f'{str(self.entry_test_command.get())}\r'
        result = self.leed_device.send_and_read_msg(command=cmd.encode())
        result = result.decode('utf-8')
        self.output_leed.config(text=result)
        self.result_label.config(text=result)
        self.update_leed_states()

    def on_leed_server_port_change(self, *args):
        self.validate_leed_ip()

    def validate_leed_ip(self, *args):
        ip_address = self.leed_server_host_entry.get()
        self.leed_device.validate_leed_ip(ip_address=ip_address)
        if self.leed_device.valid_ip:
            if not self.leed_device.leed_host == ip_address:
                self.leed_device.change_ip_address(new_ip=ip_address)
            self.validity_label.config(text="Valid IP", fg="green")
        else:
            self.validity_label.config(text="Invalid IP", fg="red")

    def clicked_load_settings(self):
        self.load_camera_settings()
        self.load_leed_settings()
        self.update_settings()

    def set_brightness(self, value):
        self.brightness = float(value)

    def set_exposure_time_absolute(self, value):
        self.exposure_time_absolute = 10000 * float(value)

    def set_gain(self, value):
        self.gain = float(value)

    # Function to set gain_auto using subprocess
    def set_auto_gain(self, camera_index, auto_gain_value):
        try:
            device = '/dev/video' + str(camera_index)
            value = '--set-ctrl=gain_auto=' + str(auto_gain_value)
            subprocess.run(['v4l2-ctl', '--device', device, value])
        except subprocess.CalledProcessError as e:
            print(f"Error setting gain to {auto_gain_value}: {e}")

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
        if new_camera_index != self.camera_index:
            self.camera_index = new_camera_index
            self.set_auto_gain(self.camera_index, self.auto_gain_value)
            self.update_settings()  # Apply the new camera settings

    def update_settings(self):
        selected_width, selected_height = self.resolutions[self.selected_resolution.get()]
        try:

            if self.camera.isOpened():
                self.camera.release()
            self.camera.set_auto_gain(self.auto_gain_value)
            self.camera.update_camera_index(self.camera_index)
            status, _ = self.camera.get_frame()
            if status:
                frame_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
                frame_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
                frame_rate = self.camera.get(cv2.CAP_PROP_FPS)

                self.frame_width_label.config(text=f"Frame Width: {frame_width}")
                self.frame_height_label.config(text=f"Frame Height: {frame_height}")
                self.frame_rate_label.config(text=f"Frame Rate: {frame_rate:.2f}")
                self.stream_status_label.config(text="Stream Status: Running", fg="green")
            else:
                # If the stream is stopped
                self.stream_status_label.config(text="Stream Status: Stopped", fg="red")
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, selected_width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, selected_height)

            self.camera.set(cv2.CAP_PROP_BRIGHTNESS, self.brightness)
            self.camera.set(cv2.CAP_PROP_GAIN, self.gain)
            self.camera.set(cv2.CAP_PROP_EXPOSURE, self.exposure_time_absolute)
            self.auto_exposure_value = 1 if not self.boolean_auto_exposure.get() else 3
            self.camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, self.auto_exposure_value)
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

    def update_settings_camera_ui(self):
        self.camera_combobox.current(self.camera_index)
        if self.selected_resolution.get() in self.resolutions:
            self.resolution_combobox.set(self.selected_resolution.get())

        self.brightness_scale.set(self.brightness)
        self.gain_scale.set(self.gain)
        self.exposure_time_entry.set(self.exposure_time)
        self.boolean_auto_gain.set(True) if self.auto_gain_value == 1 else self.boolean_auto_gain.set(False)
        self.boolean_auto_exposure.set(True) if self.auto_exposure_value == 3 else self.boolean_auto_exposure.set(False)


def main():
    try:
        cameras = list_available_cameras()
        camera_index = int(input("Enter the camera index to use: "))
        with open(script_directory + '/config.toml', 'r') as config_file:
            config = toml.load(config_file)
        if config.get('CameraSettings', {}).get('camera_index') != camera_index:
            print('The chosen camera differs from the settings in the config file.')
            camera_idx = int(input(
                'Please confirm by entering the camera index you wish to use again to overwrite the settings in the '
                'config file:'))
            config['CameraSettings']['camera_index'] = camera_idx
            camera_index = camera_idx
        with open(script_directory + '/config.toml', 'w') as config_file:
            toml.dump(config, config_file)
        if camera_index < len(cameras):
            root = tk.Tk()
            app = LCGApp(root, camera_index, cameras)
            app.update_video()  # Start the video update loop
            root.mainloop()
        else:
            print("Selected camera index is not available.")
    except ValueError:
        print("Please enter a valid camera index (an integer).")


if __name__ == "__main__":
    main()
