import numpy as np
from enum import Enum
import re
import gi
gi.require_version("Gst", "1.0")
gi.require_version("Tcam", "1.0")

from gi.repository import GLib, Gst, Tcam
class SinkFormats(Enum):
    GRAY8 = "GRAY8"
    GRAY16_LE = "GRAY16_LE"
    BGRA = "BGRx"
    BGRX = "BGRx"
def available_cameras():
    try:
        if not Gst.is_initialized():
            Gst.init(())  # Usually better to call in the main function.
    except gi.overrides.Gst.NotInitialized:
        # Older gst-python overrides seem to have a bug where Gst needs to
        # already be initialized to call Gst.is_initialized
        Gst.init(())
    monitor = Gst.DeviceMonitor.new()
    monitor.add_filter("Video/Source/tcam")
    i = 0
    serials = []
    for device in monitor.get_devices():
        struc = device.get_properties()

        print("{} : Model: {} Serial: {} {} ".format(i,
                                                     struc.get_string("model"),
                                                     struc.get_string("serial"),
                                                     struc.get_string("type")))
        i += 1
        serials.append("{}-{}".format(struc.get_string("serial"),
                                      struc.get_string("type")))
    return serials
def choose_camera(available_cameras):
    try:
        camera_index = int(input("Enter the camera index to use: "))
        #with open(script_directory + '/config.toml', 'r') as config_file:
        #    config = toml.load(config_file)
        #if config.get('CameraSettings', {}).get('camera_index') != camera_index:
        #    print('The chosen camera differs from the settings in the config file.')
        #    camera_idx = int(input(
        #        'Please confirm by entering the camera index you wish to use again to overwrite the settings in the '
        #        'config file:'))
        #    config['CameraSettings']['camera_index'] = camera_idx
        #    camera_index = camera_idx
        #with open(script_directory + '/config.toml', 'w') as config_file:
        #    toml.dump(config, config_file)
        if camera_index < len(available_cameras)+1:
            tis = TISCameraDevice()
            resolution=ResDesc(640,480,['1/1', '5/1', '15/1', '30/1', '60/1'])
            fps='1/1'
            tis.open_device(available_cameras[camera_index], resolution, fps, SinkFormats.GRAY16_LE, False)
            return tis, camera_index
        else:
            print("Selected camera index is not available.")

    except ValueError:
        print("Please enter a valid camera index (an integer).")
def get_formats(serialnumber):
    source = Gst.ElementFactory.make("tcambin")
    source.set_property("serial", serialnumber)
    source.set_state(Gst.State.READY)

    caps = source.get_static_pad("src").query_caps()
    format_dict = {}

    for x in range(caps.get_size()):
        structure = caps.get_structure(x)
        name = structure.get_name()
        try:
            videoformat = structure.get_value("format")

            width = structure.get_value("width")
            height = structure.get_value("height")

            rates = get_framerates(structure)
            tmprates = []

            for rate in rates:
                tmprates.append(str(rate))

            if type(videoformat) == Gst.ValueList:
                videoformats = videoformat
            else:
                videoformats = [videoformat]
            for fmt in videoformats:
                if videoformat not in format_dict:
                    format_dict[fmt] = FmtDesc(name, videoformat)
                format_dict[fmt].res_list.append(ResDesc(width, height, tmprates))
        except Exception as error:
            print(f"Exception during format enumeration: {str(error)}")

    source.set_state(Gst.State.NULL)
    source.set_property("serial", "")
    source = None

    return format_dict
def get_framerates(fmt):
    try:
        tmprates = fmt.get_value("framerate")
        if type(tmprates) == Gst.FractionRange:
            # A range is given only, so create a list of frame rate in 10 fps steps:
            rates = []
            rates.append("{0}/{1}".format(int(tmprates.start.num), int(tmprates.start.denom)))
            r = int((tmprates.start.num + 10) / 10) * 10
            while r < (tmprates.stop.num / tmprates.stop.denom):
                rates.append("{0}/1".format(r))
                r += 10

            rates.append("{0}/{1}".format(int(tmprates.stop.num), int(tmprates.stop.denom)))
        else:
            rates = tmprates

    except TypeError:
        # Workaround for missing GstValueList support in GI
        substr = fmt.to_string()[fmt.to_string().find("framerate="):]
        # try for frame rate lists
        field, values, remain = re.split("{|}", substr, maxsplit=3)
        rates = [x.strip() for x in values.split(",")]
    return rates
class ResDesc:
    """"""
    def __init__(self,
                 width: int,
                 height: int,
                 fps: list):
        self.width = width
        self.height = height
        self.fps = fps
        self.resolution=f"{width}x{height}"


class FmtDesc:
    """"""

    def __init__(self,
                 name: str = "",
                 fmt: str = ""):
        self.name = name
        self.fmt = fmt
        self.res_list = []

    def get_name(self):
        if self.name == "image/jpeg":
            return "jpeg"
        else:
            return self.fmt

    def get_resolution_list(self):

        res_list = []

        for entry in self.res_list:
            res_list.append(entry.resolution)

        return res_list

    def get_fps_list(self, resolution: str):

        for entry in self.res_list:
            if entry.resolution == resolution:
                return entry.fps

    def generate_caps_string(self, resolution: str, fps: str):
        if self.name == "image/jpeg":
            return "{},width={},height={},framerate={}".format(self.name,
                                                               resolution.split('x')[0],
                                                               resolution.split('x')[1],
                                                               fps)
        else:
            return "{},format={},width={},height={},framerate={}".format(self.name,
                                                                         self.fmt,
                                                                         resolution.split('x')[0],
                                                                         resolution.split('x')[1],
                                                                         fps)
class TISCameraDevice:
    def __init__(self):
        try:
            if not Gst.is_initialized():
                Gst.init(())  # Usually better to call in the main function.
        except gi.overrides.Gst.NotInitialized:
            # Older gst-python overrides seem to have a bug where Gst needs to
            # already be initialized to call Gst.is_initialized
            Gst.init(())
        # Gst.debug_set_default_threshold(Gst.DebugLevel.WARNING)
        self.serialnumber = ""
        self.height = 0
        self.width = 0
        self.framerate = "15/1"
        self.sinkformat = SinkFormats.BGRA
        self.img_mat = None
        self.ImageCallback = None
        self.pipeline = None
        self.source = None
        self.appsink = None
        # Number of frames to capture.
        self.framestocapture = 0
        # Array which will receive the images.
        self.image_data = []
        self.image_caps = None


    def open_device(self, serial,
                    resdesc, framerate,
                    sinkformat: SinkFormats,
                    showvideo: bool,
                    conversion: str = ""):
        ''' Inialize a device, e.g. camera.
        :param serial: Serial number of the camera to be used.
        :param width: Width of the wanted video format
        :param height: Height of the wanted video format
        :param framerate: Numerator of the frame rate. /1 is added automatically
        :param sinkformat: Color format to use for the sink
        :param showvideo: Whether to always open a live video preview
        :param conversion: Optional pipeline string to add a conversion before the appsink
        :return: none
        '''
        if serial is None:
            serial = self.__get_serial_by_index(0)
        self.serialnumber = serial
        self.height = resdesc.height
        self.width = resdesc.width
        self.framerate = framerate
        self.sinkformat = sinkformat
        self._create_pipeline(conversion, showvideo)
        self.source.set_property("serial", self.serialnumber)
        self.pipeline.set_state(Gst.State.READY)
        self.pipeline.get_state(40000000)

    def _create_pipeline(self, conversion: str, showvideo: bool):
        if conversion and not conversion.strip().endswith("!"):
            conversion += " !"
        p = 'tcambin name=source ! capsfilter name=caps'
        if showvideo:
            p += " ! tee name=t"
            p += " t. ! queue ! videoconvert ! ximagesink"
            p += f" t. ! queue ! {conversion} appsink name=sink"
        else:
            p += f" ! {conversion} appsink name=sink"

        try:
            self.pipeline = Gst.parse_launch(p)
        except GLib.Error as error:
            print("Error creating pipeline: {0}".format(error))
            raise

        # Quere the source module.
        self.source = self.pipeline.get_by_name("source")

        # Query a pointer to the appsink, so we can assign the callback function.
        appsink = self.pipeline.get_by_name("sink")
        appsink.set_property("max-buffers", 5)
        appsink.set_property("drop", True)
        appsink.set_property("emit-signals", True)
        appsink.set_property("enable-last-sample", True)
        appsink.connect('new-sample', self.__on_new_buffer)
        self.appsink = appsink

    def __on_new_buffer(self, appsink):
        sample = appsink.get_property('last-sample')
        if sample is not None:
            buf = sample.get_buffer()
            data = buf.extract_dup(0, buf.get_size())
            caps = sample.get_caps()
            self.img_mat = self.__convert_to_numpy(data, caps)
            self.image_caps = sample.get_caps()
            # Append the image data to the data array
            self.image_data.append(buf.extract_dup(0, buf.get_size()))
        return Gst.FlowReturn.OK

    def set_sink_format(self, sf: SinkFormats):
        self.sinkformat = sf

    def show_live(self, show: bool):
        self.livedisplay = show

    def _setcaps(self):
        """
        Set pixel and sink format and frame rate
        """
        caps = Gst.Caps.from_string('video/x-raw,format=%s,width=%d,height=%d,framerate=%s' % (
        self.sinkformat.value, self.width, self.height, self.framerate))

        capsfilter = self.pipeline.get_by_name("caps")
        capsfilter.set_property("caps", caps)

    def start_pipeline(self):
        """
        Start the pipeline, so the video runs
        """
        self.image_data = []
        self.image_caps = None

        self._setcaps()
        self.pipeline.set_state(Gst.State.PLAYING)
        error = self.pipeline.get_state(5000000000)
        if error[1] != Gst.State.PLAYING:
            print("Error starting pipeline. {0}".format(""))
            return False
        return True

    def __convert_to_numpy(self, data, caps):
        ''' Convert a GStreamer sample to a numpy array
            Sample code from https://gist.github.com/cbenhagen/76b24573fa63e7492fb6#file-gst-appsink-opencv-py-L34

            The result is in self.img_mat.
        :return:
        '''

        s = caps.get_structure(0)
        fmt = s.get_value('format')

        if (fmt == "BGRx"):
            dtype = np.uint8
            bpp = 4
        elif (fmt == "GRAY8"):
            dtype = np.uint8
            bpp = 1
        elif (fmt == "GRAY16_LE"):
            dtype = np.uint16
            bpp = 1
        else:
            raise RuntimeError(f"Unknown format in conversion to numpy array: {fmt}")

        img_mat = np.ndarray(
            (s.get_value('height'),
             s.get_value('width'),
             bpp),
            buffer=data,
            dtype=dtype)
        return img_mat

    def snap_image(self, timeout, convert_to_mat=True):
        '''
        Snap an image from stream using a timeout.
        :param timeout: wait time in second, should be a float number. Not used
        :return: Image data.
        '''
        if self.ImageCallback is not None:
            print("Snap_image can not be called, if a callback is set.")
            return None

        sample = self.appsink.emit("try-pull-sample", timeout * Gst.SECOND)
        buf = sample.get_buffer()
        data = buf.extract_dup(0, buf.get_size())
        if convert_to_mat and sample is not None:
            try:
                self.img_mat = self.__convert_to_numpy(data, sample.get_caps())
            except RuntimeError:
                # unsuported format to convert to mat
                # ignored to keep compatibility to old sample code
                pass

        return data
    def get_captured_image_count(self):
        '''
        Return the count of captured images, which is the len of
        the image data array
        '''
        return(len(self.image_data))
    def get_image(self):
        return self.img_mat

    def get_image_from_buffer(self, image_nr: int):
        '''
        Return a numpy array which contains the image data of the
        image at array position image_nr.
        If image_nr is out of bounds, then None is returned.
        '''
        print(image_nr, len(self.image_data), image_nr>len(self.image_data))
        if image_nr > len(self.image_data):
            return None
        print(self.image_caps)
        if self.image_caps is None:
            return None

        return self.__convert_to_numpy(self.image_data[image_nr],
                                       self.image_caps)
    def stop_pipeline(self):
        self.pipeline.set_state(Gst.State.PAUSED)
        self.pipeline.set_state(Gst.State.READY)

    def get_source(self):
        '''
        Return the source element of the pipeline.
        '''
        return self.source

    def list_properties(self):
        property_names = self.source.get_tcam_property_names()

        for name in property_names:
            try:
                base = self.source.get_tcam_property(name)
                print("{}\t{}".format(base.get_display_name(),
                                      name))
            except Exception as error:
                raise RuntimeError(f"Failed to get property '{name}'") from error

    def get_property(self, property_name):
        """
        Return the value of the passed property.
        If something fails an
        exception is thrown.
        :param property_name: Name of the property to set
        :return: Current value of the property
        """
        try:
            baseproperty = self.source.get_tcam_property(property_name)
            val = baseproperty.get_value()
            return val

        except Exception as error:
            raise RuntimeError(f"Failed to get property '{property_name}'") from error

        return None

    def set_property(self, property_name, value):
        '''
        Pass a new value to a camera property. If something fails an
        exception is thrown.
        :param property_name: Name of the property to set
        :param value: Property value. Can be of type int, float, string and boolean
        '''
        try:
            baseproperty = self.source.get_tcam_property(property_name)
            baseproperty.set_value(value)
        except Exception as error:
            raise RuntimeError(f"Failed to set property '{property_name}'") from error

    def execute_command(self, property_name):
        '''
        Execute a command property like Software Trigger
        If something fails an exception is thrown.
        :param property_name: Name of the property to set
        '''
        try:
            baseproperty = self.source.get_tcam_property(property_name)
            baseproperty.set_command()
        except Exception as error:
            raise RuntimeError(f"Failed to execute '{property_name}'") from error

    def set_image_callback(self, function, *data):
        self.ImageCallback = function
        self.ImageCallbackData = data

    def __get_serial_by_index(self, index: int):
        ' Return the serial number of the camera enumerated at given index'
        monitor = Gst.DeviceMonitor.new()
        monitor.add_filter("Video/Source/tcam")
        devices = monitor.get_devices()
        if (index < 0) or (index > len(devices) - 1):
            raise RuntimeError("Index out of bounds")
        device = devices[index]
        return device.get_properties().get_string("serial")
    def isRunning(self):
        status=self.pipeline.get_state(50000000)
        if status[-1]==Gst.State.VOID_PENDING:
            return status[1]==Gst.State.PLAYING
        else:
            return False