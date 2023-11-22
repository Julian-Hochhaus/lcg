import cv2
import subprocess
class CameraDevice:
    def __init__(self, camera_index):
        self.camera_index = camera_index
        self.cap = cv2.VideoCapture(camera_index, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"FFV1"))
        self.camera_active=self.get_state()


    def get(self, PROP):
        return self.cap.get(PROP)
    def set(self,PROP, value):
        self.cap.set(PROP, value)
    def get_state(self):
        ret, frame = self.cap.read()
        if ret:
            return True
        else:
            return False
    def get_frame(self):
        ret, frame = self.cap.read()
        if ret:
            self.camera_active=True
            return self.camera_active,cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            self.camera_active=False
            return self.camera_active,None

    def update_camera_index(self, new_camera_index):
        if self.cap.isOpened():
            self.cap.release()  # Release the old device

        self.camera_index = new_camera_index
        self.cap = cv2.VideoCapture(new_camera_index, cv2.CAP_V4L2)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"FFV1"))

    def set_auto_gain(self, auto_gain_value):
        try:
            device = '/dev/video' + str(self.camera_index)
            value = '--set-ctrl=gain_auto=' + str(auto_gain_value)
            subprocess.run(['v4l2-ctl', '--device', device, value])
        except subprocess.CalledProcessError as e:
            print(f"Error setting gain auto to {auto_gain_value}: {e}")
    def isOpened(self):
        return self.cap.isOpened()
    def release(self):
        self.cap.release()
    def close_camera(self):
        if self.cap.isOpened():
            self.cap.release()
