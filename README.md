# *LCG:* GUI for LEED Device and CCD-camera Control
This project is a graphical user interface (GUI) designed to control a SPECS ErLEED digital controller and a CCD-camera from The Imaging Source. 

The application allows users to manage settings of the camera and the ErLEED.

Thereby, the user is able to get camera and ErLEED device state, to capture images, change several camera properties (e.g. brightness, gain, and exposure time) and set the kinetic energy of the LEED electrons.
The program includes the possibility to record I(V)-series.


This application is divided into three parts:
1. The main GUI, which is started running `gui.py`
2. The `LEEDDevice` class, which handles all the communication with the ErLEED device,
3. And the `CameraDevice class, which handles the camera.

The CameraDevice as well as the LEEDDevice class could be used independently in other projects.


## Installation
### Install via pip
```
pip install leedcameragui
```
### Manual Installation
#### Steps to run the program
The code was written and tested using Python 3.10.12, however it should run on other Python 3.xx.xx as well.
1. Clone this repository.
2. Please make sure, that your installation contains all the following packages:
```
opencv-python>=4.8.1.78
Pillow>=9.0.1
numpy>=1.26.2
toml>=0.10.2
```
The program was tested using the given versions, probably will work with some older versions too.

Install requirements e.g. using:
``` 
pip install -r requirements.txt
```
3. Inside the cloned folder, run `python gui.py` to start the application.

### Usage
Launch the application by running gui.py.
![Main GUI window](https://github.com/Julian-Hochhaus/lcg/blob/main/documentation/main_window.png)

The main window holds in the upper half on the left the livefeed of the choosen camera. On the right side of the upper half, the last saved image will be displayed.

Use the buttons to perform specific actions like setting energy levels, capturing images, and recording I(V)-image series. Status of the LEED device as wel as of the camera feed are displayed as well.

TODO: explain I(V) handling as well as calibration curve.

By pressing `Òpen Settings`, the settings window will appear, where you are able to manipulate camera settings as well as generate a gain calibration curve for I(V) image series. In addition, arbitrary commands to the ErLEED could be send here too. 
![Settings window](https://github.com/Julian-Hochhaus/lcg/blob/main/documentation/settings_window.png)

### Configuration

In the `config.toml`file, several configuration properties are available:

TODO: List properties and explain handling of config file

### Contributing
Contributions to this project are welcome! Please fork the repository, make changes, and submit pull requests. Bug reports, feature requests, and feedback are appreciated.

### License
This project is licensed under the MIT License - see the LICENSE file for details.

#### Credits
Contributors: [Julian Hochhaus](https://github.com/Julian-Hochhaus)

