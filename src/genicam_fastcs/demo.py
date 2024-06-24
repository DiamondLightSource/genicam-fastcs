import ipaddress
from datetime import datetime

import cv2
import numpy as np
from genicam.genapi import AccessException, LogicalErrorException
from harvesters.core import Harvester

WIDTH = 1920  # Image buffer width
HEIGHT = 1200  # Image buffer height
PIXEL_FORMAT = "Mono8"  # Camera pixel format
SDK_CTI_PATH = (
    "/opt/mvIMPACT_Acquire/lib/x86_64/mvGenTLProducer.cti"  # Common transport interface
)
# CAMERA_SERIAL = "50-0536906292"  # Camera product model
# CAMERA_SERIAL = "50-0503346450"  # Camera product model
CAMERA_SERIAL = "17497407"  # Camera product model
FPS = 120  # 32
OUTPUT = "RESULT"  # video name (without extension)
N_FRAMES = 120
CHANNELS = 1
GAIN = 30


class GenICamNotFoundError(Exception):
    pass


class GenICam:
    def __init__(self):
        self.h = Harvester()  # GenICam consumer
        self.h.add_file(SDK_CTI_PATH)  # Add GenICam producer
        self.h.update()

        print(self.h.device_info_list)
        self._print_link_info("serial_number", CAMERA_SERIAL)

        print("[INFO] Connecting to camera, please wait...")
        self.ia = self.h.create({"serial_number": CAMERA_SERIAL})  # Image acquirer

        self.ia.remote_device.node_map.Width.value = WIDTH
        self.ia.remote_device.node_map.Height.value = HEIGHT
        self.ia.remote_device.node_map.PixelFormat.value = PIXEL_FORMAT

        if CAMERA_SERIAL == "17497407":
            self.ia.remote_device.node_map.AcquisitionFrameRateEnable.value = True
            self.ia.remote_device.node_map.AcquisitionFrameRate.value = FPS
            self.ia.remote_device.node_map.GainAuto.value = "Off"
        else:
            self.ia.remote_device.node_map.AcquisitionFrameRateAbs.value = FPS

        self.ia.remote_device.node_map.Gain.value = GAIN

    def _print_link_info(self, key, value):
        dev_parent = None
        for dev_info in self.h.device_info_list:
            dev_dict = dev_info._property_dict
            if key in dev_dict:
                if dev_dict[key] == value:
                    dev_parent = dev_info.parent
                    break
        if not dev_parent:
            raise GenICamNotFoundError
        int_address = dev_parent.node_map.GevDeviceIPAddress.value
        ip_address = str(ipaddress.ip_address(int_address))
        int_subnet = dev_parent.node_map.GevDeviceSubnetMask.value
        subnet_addr = str(ipaddress.ip_address(int_subnet))
        link_speed = dev_parent.node_map.mvGevInterfaceLinkSpeed.value
        print(f"[INFO] IP Address: {ip_address}")
        print(f"[INFO] Subnet: {subnet_addr}")
        print(f"[INFO] Link speed is {link_speed} Mbps")

    def run(self, output):
        # Preallocate an array that will temporarily store frames
        # frames = np.zeros([N_FRAMES, HEIGHT, WIDTH, CHANNELS], dtype=np.uint8)
        frames = np.zeros([N_FRAMES, HEIGHT, WIDTH], dtype=np.uint8)

        # Store frames in RAM
        start_time = datetime.now()
        self.ia.start()  # start image acquisition
        for i in range(N_FRAMES):
            with self.ia.fetch(timeout=3) as buffer:
                frames[i] = buffer.payload.components[0].data.reshape(
                    buffer.payload.components[0].height,
                    buffer.payload.components[0].width,
                    # CHANNELS,
                )
        self.ia.stop()  # stop image acquisition
        delta_t = (datetime.now() - start_time).total_seconds()

        expected_t = N_FRAMES / FPS
        transferred_data = frames.nbytes / 1e6
        print(
            f"Transfered: {transferred_data} MB in {delta_t}s (expected {expected_t}s)"
        )
        print(f"Expected Transfer Speed: {transferred_data/expected_t} MB/s")
        print(f"Measured Transfer Speed: {transferred_data/delta_t} MB/s")

        out = cv2.VideoWriter(
            output + ".avi",
            cv2.VideoWriter_fourcc(*"MP42"),
            FPS,
            (WIDTH, HEIGHT),
        )

        # After all frames have been grabbed safely, write output video
        for i in range(len(frames)):
            out.write(cv2.cvtColor(frames[i], cv2.COLOR_GRAY2BGR))
        out.release()

    def print_temperature(self):
        temp = self.ia.remote_device.node_map.DeviceTemperature.value
        print(f"Temperature: {temp}C")

    def print_exposure_enums(self):
        symbs = (
            self.ia.remote_device.node_map.ExposureAuto.symbolics
        )  # Only defined for IEnumerations
        print(symbs)

    def _list_children(self, object, key):
        child_list = []
        map = self.ia.remote_device.node_map
        for item in dir(map):
            try:
                if hasattr(getattr(map, item), key):
                    child_list.append(item)
            except AccessException:
                pass
            except LogicalErrorException:
                pass
        return child_list

    def list_commands(self):
        """ICommand interfaces"""
        map = self.ia.remote_device.node_map
        return self._list_children(map, "execute")

    def list_attributes(self):
        """IEnumeration, IBoolean, IFloat, IInteger interfaces"""
        map = self.ia.remote_device.node_map
        return self._list_children(map, "value")

    def __del__(self):
        self.ia.destroy()
        self.h.reset()  # Needed? Need to add .update to init?


# def validate_frames(file, expected_count):
#     print(f"Validating {expected_count} frames")

#     invalid_frames = 0
#     for cnt in range(expected_count):
#         if np.sum(frame) == 0:
#             invalid_frames = +1

#     print(f"Found {invalid_frames} invalid frames out of {expected_count}")


if __name__ == "__main__":
    dev = GenICam()
    dev.print_temperature()
    dev.print_exposure_enums()
    print(dev.list_commands())
    print(dev.list_attributes())
    dev.run(OUTPUT)
    # validate_frames(OUTPUT)
