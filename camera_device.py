import cv2
class CameraDevice:
    def __init__(self, camera_index):
        self.camera_index = camera_index
        self.cap = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)
        self.resolutions = self.load_resolutions()
        self.brightness = 100
        self.gain = 100
        self.exposure_time = 0.5

    def load_resolutions(self):
        resolutions = {}
        # Implement loading resolutions logic here
        return resolutions

    def set_brightness(self, value):
        self.brightness = float(value)
        self.cap.set(cv2.CAP_PROP_BRIGHTNESS, self.brightness)

    def set_gain(self, value):
        self.gain = float(value)
        self.cap.set(cv2.CAP_PROP_GAIN, self.gain)

    def set_exposure_time_absolute(self, value):
        self.exposure_time = 10000 * float(value)
        self.cap.set(cv2.CAP_PROP_EXPOSURE, self.exposure_time)

    def get_frame(self):
        ret, frame = self.cap.read()
        if ret:
            return frame
        else:
            return None

    def close_camera(self):
        if self.cap.isOpened():
            self.cap.release()