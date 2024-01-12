import sys
import os
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject
from PyQt5.QtGui import QImage
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget
import cv2
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from TIS import TIS
import numpy as np

script_directory = os.path.dirname(os.path.abspath(__file__))
settings_window = None
__version__ = "0.4.2"


class CircularBuffer:
    def __init__(self, size):
        self.size = size
        self.frames = [None] * size
        self.index = 0

    def add_frame(self, frame):
        self.frames[self.index] = frame.copy()  # Make a copy to avoid overwriting
        self.index = (self.index + 1) % self.size

    def get_frames(self):
        return [frame for frame in self.frames if frame is not None]


class VideoUpdater(QObject):
    frame_updated = pyqtSignal(np.ndarray)

    def __init__(self, tis, circular_buffer):
        super().__init__()
        self.tis = tis
        self.is_running = False
        self.circular_buffer = circular_buffer

    def start_streaming(self):
        self.is_running = True
        while self.is_running:
            frame = self.tis.get_image()
            if frame is not None and frame.any():
                self.frame_updated.emit(frame)
                self.circular_buffer.add_frame(frame)
            QThread.msleep(1000)  # Adjust the sleep interval to control the acquisition rate
        self.tis.stop_pipeline()

    def stop_pipeline(self):
        self.is_running = False
class LCGApp(QMainWindow):
    def __init__(self, ser, tis, idx):
        super(LCGApp, self).__init__()

        self.ser = ser
        self.tis = tis
        self.idx = idx

        self.setWindowTitle(f"LCG: LEED Camera GUI v.{__version__}")
        self.setGeometry(100, 100, 1400, 1020)
        self.setMaximumSize(1920, 1100)

        fmt = TIS.get_formats(ser[0])
        res = fmt.get('GRAY16_LE').res_list[0]
        fps = fmt.get('GRAY16_LE').get_fps_list('640x480')[0]
        tis.open_device(ser[idx], res, fps, TIS.SinkFormats.GRAY16_LE, False)
        tis.start_pipeline()
        tis.set_property('Gain', 0)
        tis.set_property('ExposureTime', 10000)
        tis.set_property('BlackLevel', 0)

        self.circular_buffer = CircularBuffer(size=10)  # Adjust the size as needed

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.videoframes = QVBoxLayout(self.central_widget)

        self.figure, self.ax = plt.subplots()
        self.img_plot = self.ax.imshow(np.zeros((480, 640)), cmap='gray')
        plt.axis('off')
        plt.tight_layout()

        self.canvas = FigureCanvas(self.figure)
        self.videoframes.addWidget(self.canvas)

        self.video_label = QLabel(self.central_widget)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.videoframes.addWidget(self.video_label)

        self.timer = QTimer(self)

        self.video_updater = VideoUpdater(tis, self.circular_buffer)
        self.video_thread = QThread()
        self.video_updater.moveToThread(self.video_thread)

        self.timer.timeout.connect(self.video_updater.start_streaming)
        self.video_updater.frame_updated.connect(self.update_video_frame)

        self.showEvent = self.on_show_event

        self.on_closing_event = None

    def on_show_event(self, event):
        self.timer.start(1000)  # Update every 1000 milliseconds (1 second)
        self.video_thread.start()
        self.showEvent = self.showEvent

    def update_video_frame(self, frame):
        actual_width = self.tis.width
        actual_height = self.tis.height
        ratio = float(actual_width / actual_height)
        new_width = int(480 * ratio)
        new_height = int(480)
        resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
        image_8bit = (resized_frame / 256).astype(np.uint8)
        self.img_plot.set_data(image_8bit)
        self.figure.canvas.draw_idle()
        plt.imshow(resized_frame, cmap='Greys_r')
        self.canvas.draw()

        recent_frames = self.circular_buffer.get_frames()
        # Use recent_frames as necessary

    def closeEvent(self, event):
        self.timer.stop()
        self.video_updater.stop_pipeline()
        self.video_thread.quit()
        self.video_thread.wait()
        self.tis.stop_pipeline()
        if self.on_closing_event:
            self.on_closing_event()
        event.accept()


def main():
    ser = TIS.available_cameras()
    tis, idx = TIS.choose_camera(ser)
    app = QApplication(sys.argv)
    main_window = LCGApp(ser=ser, tis=tis, idx=idx)

    main_window.on_closing_event = main_window.video_updater.stop_pipeline

    main_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
