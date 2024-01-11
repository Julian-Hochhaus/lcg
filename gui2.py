import sys, os
import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter.filedialog as filedialog
from TIS import TIS
import cv2

script_directory = os.path.dirname(os.path.abspath(__file__))
settings_window = None
__version__ = "0.4.2"


class LCGApp:
    def __init__(self, root, ser, tis, idx):
        self.root = root
        self.root.title(f"LCG: LEED Camera GUI v.{__version__}")
        self.root.geometry("1400x1020")
        self.root.maxsize(width=1920, height=1100)
        self.tis = tis

        fmt = TIS.get_formats(ser[0])
        res = fmt.get('GRAY16_LE').res_list[0]
        fps = fmt.get('GRAY16_LE').get_fps_list('640x480')[0]
        tis.open_device(ser[idx], res, fps, TIS.SinkFormats.GRAY16_LE, False)
        tis.start_pipeline()
        tis.set_property('Gain', 0)
        tis.set_property('ExposureTime', 10000)
        tis.set_property('BlackLevel', 0)

        # structure of GUI
        self.videoframes = tk.Canvas(root, width=1380, height=490)
        self.videoframes.pack(side='top')
        self.videoframes.update()

        # Create a frame to hold the Matplotlib plot
        self.live_frame = tk.Label(self.videoframes, text="Livefeed")
        self.livefeed_window = self.videoframes.create_window(self.videoframes.winfo_width() // 4,
                                                              self.videoframes.winfo_height() / 2,
                                                              window=self.live_frame, anchor=tk.CENTER)
        x1, y1, _, _ = self.videoframes.bbox(self.livefeed_window)
        self.videoframes.create_rectangle(x1 + self.live_frame.winfo_reqwidth() // 2 - 320,
                                          y1 + self.live_frame.winfo_reqheight() // 2 - 240,
                                          x1 + self.live_frame.winfo_reqwidth() // 2 + 320,
                                          y1 + self.live_frame.winfo_reqheight() // 2 + 240, fill="grey95",
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

        # Create a Matplotlib figure and axis for displaying the camera feed
        self.figure, self.ax = plt.subplots()
        self.img_plot = self.ax.imshow(np.zeros((480, 640)), cmap='gray')  # Initialize with a blank image
        plt.axis('off')  # Hide axes
        plt.tight_layout()

        # Create a Tkinter canvas for embedding Matplotlib plot
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.live_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack()

        # Schedule the next update after 100 milliseconds
        self.root.after(100, self.update_stream)

    # Function to update the video stream in the Matplotlib plot
    def update_stream(self):
        if self.tis.isRunning():
            frame = self.tis.get_image()  # Get the image from the camera
            if frame is not None and frame.any():
                actual_width = self.tis.width
                actual_height = self.tis.height
                # Calculate the ratio to maintain a minimum height of 480 pixels
                ratio = float(actual_width / actual_height)
                new_width = int(480 * ratio)
                new_height = int(480)
                resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
                print(np.max(resized_frame))
                image_8bit = (resized_frame / 256).astype(np.uint8)  # Convert to 8-bit for display
                self.img_plot.set_data(image_8bit)  # Update the plot
                self.figure.canvas.draw_idle()
                plt.imshow(resized_frame, cmap='Greys_r')
                self.canvas.draw()

        # Schedule the next update after 100 milliseconds
        self.root.after(100, self.update_stream)


def main():
    ser = TIS.available_cameras()
    tis, idx = TIS.choose_camera(ser)
    root = tk.Tk()
    app = LCGApp(root, ser=ser, tis=tis, idx=idx)
    root.mainloop()
    app.tis.stop_pipeline()  # Ensure to properly close the TIS camera when the tkinter window is closed


if __name__ == "__main__":
    main()
