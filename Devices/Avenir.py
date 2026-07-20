# Based on basic_spectrometer from the Avenir SDK, Copyright 2023 by Avenir Photonics GmbH & Co. KG
#
# All added code is copyright (C) 2026 Bence Göblyös
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see https://www.gnu.org/licenses/.


"""
This module provides the high-level object-oriented interface to control and
stream data from Avenir ARIS compact spectrometers. It handles the low-level
USB polling, handles exposure adjustment, and parses raw metadata.

Examples
--------
Below is a minimum working example showing how to initialize the spectrometer,
set up automatic exposure and capture a single spectrum:

.. code-block:: python

    import matplotlib.pyplot as plt
    from Devices.Avenir import ARIS

    # Initialize the device (automatically searches for the USB interface)
    spec = ARIS()

    if spec.device is not None:
        # Set automatic exposure. This will set the exposure time and averaging automatically
        # such that the total integration time is 20 ms.
        spec.setAutoExposure(exposure_us=200000)

        # Capture the data
        data = spec.capture()

        if data:
            print(f"Captured spectrum at {data['temperature_c']}°C")
            plt.plot(data['wavelengths'], data['spectrum']")
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

def _enum(**enums):
    """
    Creates a simple enumeration type from keyword arguments.

    Parameters
    ----------
    **enums: dict
        Keyword arguments representing the enumeration keys and values.

    Returns
    -------
    Enum: type
        A new class acting as an enumeration.
    """
    return type('Enum', (), enums)


# Values of Spectrometer Status
_SpectrStatus = _enum(
    Idle=0x00,
    WaitingForTrigger=0x01,
    TakingSpectrum=0x02,
    WaitingForTemperature=0x03,
    PoweredOff=0x08,
    SleepMode=0x09,
    NotConnected=0x0A
)

def _find_address(**kwargs):
    """
    Finds and returns the first compatible Avenir USB spectrometer device.

    Parameters
    ----------
    **kwargs: dict
        Arguments to pass to LibusbInterface.find_interfaces.

    Returns
    -------
    device: object or None
        The first matching USB device interface, or None if no device is found.
    """
    # Find all interfaces
    devices = LibusbInterface.find_interfaces(**kwargs)
    devices = [d for d in devices if d.idVendor == 0x354F and 0x0100 <= d.idProduct <= 0x01FF]

    if len(devices) > 0:
        return devices[0]
    else:
        return None

class ARIS():
    """
    Driver class for Avenir ARIS compact spectrometers.

    Manages USB connection, device configuration, and spectrum capture.
    """
    def __init__(self, **kwargs):
        """
        Parameters
        ----------
        **kwargs: dict
            Keyword arguments passed to _find_address() to manually select a USB device.
            Valid keywords are "idVendor" and "idProduct", corresponding to the vendor
            and product ID of the manually defined USB device.
        """
        # Set up logger
        self.logger = logging.getLogger('instrumpy.ARIS')
        self.logger.propagate = True
        self.logger.setLevel(logging.NOTSET)
        self.logger.debug("Logger initialized.")

        self.device = _find_address(**kwargs)

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
        """
        Closes the USB connection when the object is destroyed.
        """
        if self.ziolink is not None:
            self.ziolink.close()

    def setExposure(self, exposure_us = 1000, average = 1):
        """
        Sets the exposure time and number of averages for spectral capture.

        Parameters
        ----------
        exposure_us: int, default: 1000
            Exposure time in microseconds.
        average: int, default: 1
            Number of spectra to average.
        """
        self.ziolink.send_receive_message(0x1109, 0)                # 0x1109 = Set Parameter: AutoExposureEnabled
        self.ziolink.send_receive_message(0x1100, int(exposure_us)) # 0x1100 = Set Parameter: ExposureTime (in microseconds)
        self.ziolink.send_receive_message(0x1101, int(average))     # 0x1101 = Set Parameter: Averaging

    def setAutoExposure(self, target_us = 200000):
        """
        Enables automatic exposure and specifies target integration time.

        Parameters
        ----------
        exposure_us: int, default: 200000
            Target integration time in microseconds.
        """
        self.ziolink.send_receive_message(0x1109, 1)              # 0x1109 = Set Parameter: AutoExposureEnabled
        self.ziolink.send_receive_message(0x110A, int(target_us)) # 0x110A = Set Parameter: AutoExposureTime

    def capture(self):
        """
        Captures a single spectrum and retrieves associated metadata.

        Returns
        -------
        result: dict or None
            A dictionary containing the wavelength array, spectrum intensities,
            exposure settings, device temperature, and other capture metadata.
            Returns None if the received data stream is invalid.
        """
        self.ziolink.send_receive_message(0x0004, 1) # Start capture with a single spectrum
        # TODO: implement multiple spectrum capture

        # Wait for completion
        status = _SpectrStatus.TakingSpectrum
        available_spectra = 0
        while status == _SpectrStatus.TakingSpectrum or status == _SpectrStatus.WaitingForTrigger:
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
            self.logger.warning(f'High spectrometer load ({"{:.2f}".format(100*load_level)}%)')

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
