"""
Based on basic_spectrometer from the Avenir SDK, Copyright 2023 by Avenir Photonics GmbH & Co. KG

All added code is copyright (C) 2026 Bence Göblyös

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, version 3.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see https://www.gnu.org/licenses/.
"""

import sys
import struct
import logging
import time
import numpy as np
import pandas as pd

# Include SDK
from Libraries.ARIS.libusb_interface import LibusbInterface
from Libraries.ARIS.ziolink_protocol import ZioLinkProtocol

def enum(**enums):
    return type('Enum', (), enums)


# Values of Spectrometer Status
SpectrStatus = enum(
    Idle=0x00,
    WaitingForTrigger=0x01,
    TakingSpectrum=0x02,
    WaitingForTemperature=0x03,
    PoweredOff=0x08,
    SleepMode=0x09,
    NotConnected=0x0A
)

def find_address(**kwargs):
    # Find all interfaces
    devices = LibusbInterface.find_interfaces(**kwargs)
    devices = [d for d in devices if d.idVendor == 0x354F and 0x0100 <= d.idProduct <= 0x01FF]

    if len(devices) > 0:
        return devices[0]
    else:
        return None

"""
Avenir ARIS compact spectrometer
"""
class ARIS():
    def __init__(self, **kwargs):
        # Set up logger
        self.logger = logging.getLogger('instrumpy.ARIS')
        self.logger.propagate = True
        self.logger.setLevel(logging.NOTSET)
        self.logger.debug("Logger initialized.")
        
        # Filter arguments to idVendor and idProduct
        usb_args = foodict = {k: v for k, v in kwargs.items() if k in ["idVendor", "idProduct"]}
        self.device = find_address(**usb_args)

        if self.device is not None:
            self.ziolink = ZioLinkProtocol(self.device)
            self.logger.debug("Opened ARIS device for communication.")
        else:
            self.ziolink = None
            self.logger.error("Did not find a suitable USB device.")
            return None

        self.ziolink.open()
        self.ziolink.send_receive_message(0x0000) # Send reset command

        # Gather basic system data
        model_name_bytes = self.ziolink.send_receive_message(0x2003)  # 0x2003 = Get Device Property: ModelName
        if model_name_bytes[-1] == 0:
            model_name_bytes = model_name_bytes[:-1]  # strip trailing null terminator
        self.model = str(model_name_bytes, "utf-8")

        serial_number_bytes = self.ziolink.send_receive_message(0x2001)  # 0x2001 = Get Device Property: SerialNumber
        if serial_number_bytes[-1] == 0:
            serial_number_bytes = serial_number_bytes[:-1]  # strip trailing null terminator
        self.serial = str(serial_number_bytes, "utf-8")

        pixel_count_bytes = self.ziolink.send_receive_message(0x2007)  # 0x2007 = Get Device Property: PixelCount
        pixel_count = int.from_bytes(pixel_count_bytes, 'little')
        self.pixels = int.from_bytes(pixel_count_bytes, 'little')

        self.logger.info(f"Model: {self.model}, Serial: {self.serial}, CCD size: {self.pixels}")

        # Get wavelength calibration
        c = [0]*4
        for i in range(0, 4):
            wavelengths_bytes = self.ziolink.send_receive_message(0x201C + i)  # 0x201C = Get Device Property: WavelengthCoeff0
            c[i] = struct.unpack('<f', wavelengths_bytes[0:4])[0]

        self.wavelengths = [c[0] + c[1]*p + c[2]*(p**2) + c[3]*(p**3) for p in range(0, self.pixels)]
        self.logger.info("Wavelength range: " + "{:.2f}".format(self.wavelengths[0]) + " to " +
          "{:.2f}".format(self.wavelengths[-1]) + " nm")

    def __del__(self):
        if self.ziolink is not None:
            self.ziolink.close()

    def setExposure(self, exposure_us = None, average = 1):
        if exposure_us is None:
            # Enable automatic exposure
            self.ziolink.send_receive_message(0x1109, 1)                 # 0x1109 = Set Parameter: AutoExposureEnabled
            self.ziolink.send_receive_message(0x1101, int(average))      # 0x1101 = Set Parameter: Averaging

        else:
            self.ziolink.send_receive_message(0x1100, int(exposure_us))  # 0x1100 = Set Parameter: ExposureTime (in microseconds)
            self.ziolink.send_receive_message(0x1101, int(average))      # 0x1101 = Set Parameter: Averaging
            self.ziolink.send_receive_message(0x1109, 0)                 # 0x1109 = Set Parameter: AutoExposureEnabled

    def capture(self):
        self.ziolink.send_receive_message(0x0004, 1) # Start capture with a single spectrum
        # TODO: implement multiple spectrum capture
        
        # Wait for completion
        status = SpectrStatus.TakingSpectrum
        available_spectra = 0
        while status == SpectrStatus.TakingSpectrum or status == SpectrStatus.WaitingForTrigger:
            st_bytes = self.ziolink.send_receive_message(0x3000)  # 0x3000 = Get Measured Value: Status
            status = st_bytes[0]  # byte 0 of returned value
            available_spectra = st_bytes[1] + 256 * st_bytes[2]  # //byte 1 and 2 of returned value

        rawdata = self.ziolink.send_receive_message(0x4000)
        if len(rawdata) != 64 + self.pixels * 4:
            self.logger.error("Unexpected number of bytes in spectrum data stream.")
            return None

        exposure_us = struct.unpack("<I", rawdata[0:4])[0]
        averaging = struct.unpack("<I", rawdata[4:8])[0]
        time_ms = struct.unpack("<I", rawdata[8:12])[0] / 10.0
        date_days = struct.unpack("<I", rawdata[12:16])[0]
        load_level = struct.unpack("<f", rawdata[16:20])[0]
        temperature_c = struct.unpack("<f", rawdata[20:24])[0]
        exposure_settings = struct.unpack("<H", rawdata[28:30])[0]
        applied_processing = struct.unpack("<H", rawdata[30:32])[0]
        spectrum = [struct.unpack("<f", rawdata[p * 4 + 64:p * 4 + 68])[0] for p in range(self.pixels)]
        dark_avg = struct.unpack("<f", rawdata[56:60])[0]
        readout_noise = struct.unpack("<f", rawdata[60:64])[0]

        if load_level >= 0.95:
            self.logger.warning(f'High spectrometer load ({round(100*results["load_level"])}%)')
        
        return {
            "wavelengths": self.wavelengths,
            "spectrum": spectrum,
            "exposure_us": exposure_us,
            "averaging": averaging,
            "uptime_s": date_days * 24 * 3600 + time_ms/1000,
            "load_level": load_level,
            "temperature_c": temperature_c,
            "exposure_settings": exposure_settings,
            "applied_processing": applied_processing,
            "dark_avg": dark_avg,
            "readout_noise": readout_noise,
            "timestamp_unix_ns": time.time_ns(),  
        }