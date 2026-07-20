"""
Copyright (C) 2025-2026 Bence Göblyös

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, version 3.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see https://www.gnu.org/licenses/.
"""

import serial      # Serial communication
import time        # Timeout handling
import numpy as np # Math
import logging

# TODO: split into two parts. The legacy should use serial, while the new one should be reimplemented with pyvisa for graceful failures.


class MKULO813PLL():
    """
    Kuhne MKU LO 8-13 PLL driver class. Supports both v1 and v2 firmware.
    """
    def __init__(self, port, timeout = 1.0, legacy = False):
        """
        Parameters
        ----------
        port: str
            Seirial port of the device. Examples: 'COM3' on Windows, '/dev/ttyACM0' on Linux.
        timeout: float, default: 1.0
            Communication timeout in seconds.
        legacy: bool, default: False
            If True, uses the comminication protocol for the older v1.x firmware.
            If False, uses the more modern command set and syntax the v2.x firmware.
        """
        # Set up logger
        self.logger = logging.getLogger('instrumpy.KuhnePLL')
        self.logger.propagate = True
        self.logger.setLevel(logging.NOTSET)
        self.logger.debug("Logger initialized.")
        
        self.device = None
        self.port = port
        self.connect_timeout = timeout
        self.legacy = legacy
        self._connect()
        
    def __del__(self):
        self.device.close()
        
    def _connect(self):
        """
        Open connection on the serial port.
        """
        try:
            self.device = serial.Serial(
                port = self.port,
                baudrate = 115200,
                bytesize = serial.EIGHTBITS,
                parity = serial.PARITY_NONE,
                stopbits = serial.STOPBITS_ONE,
                timeout = self.connect_timeout,
            )
            return True
        except serial.SerialException as err:
            self.logger.error(f"Failed to connect to oscillator with reason: {err}")
            self.device = None
            return False

    def sendCommand(self, cmd, timeout = 1.0, capture_output = True):
        """
        Sends a command to the device.

        Parameters
        ----------
        cmd: str
            Command to be sent.
        timeout: float, default: 1.0
            Communication timeout in seconds.
        capture_output: bool, default: True
            Whether or not to capture the response.

        Returns
        -------
        nchar: int
            Number of characters transmitted. -1 indicates a transmission failure.
        resp: str
            Response from device. None if response is not captured.
            If ``nchar == -1``, resp will contain the error message.
        """
        try:
            self.device.reset_input_buffer()
            nchar = self.device.write(cmd.encode())
            time.sleep(timeout)

            if capture_output:
                resp = self.device.read_all().decode().strip()
                return nchar, resp

            else:
                return nchar, None 

        except serial.SerialException as err:
            self.logger.error(f"Sending command to oscillator failed with reason: {err}")
            return -1, err

    def setHz(self, val, retries = 3):
        """
        Sets the oscillator frequency in Hz.

        Parameters
        ----------
        val: int
            Target frequency in Hz.
        retries: int, default: 3
            Number of retransimssions in case of failure.

        Returns
        -------
        success: bool
            True if successful, False otherwise.
        """
        if self.device is None:
            self.logger.error("Device is not open, cannot set frequency.")
            return False

        hz = str(round((np.floor(val) % 1000))).zfill(3)
        khz = str(round(np.floor(val*1e-3) % 1000)).zfill(3)
        mhz = str(round(np.floor(val*1e-6) % 1000)).zfill(3)
        ghz = str(round(np.floor(val*1e-9) % 1000)).zfill(3)

        
        for (freq, prefix) in zip([ghz, mhz, khz, hz], ["G", "M", "k", "H"]):
            if self.legacy:
                cmd = f"{freq}{prefix}F1"
            else:
                cmd = f"{prefix}FR{freq}\r\n"
            
            # Attempt transmission multiple times
            successful = True
            for attempt in range(retries + 1):
                if attempt != 0:
                    self.logger.warning(f"Sending command failed, retrying (attempt {attempt}/{retries}).")
                
                nchar, resp = self.sendCommand(cmd, timeout = 0.015, capture_output = True)
                if nchar != -1 and resp == "A":
                    successful = True
                    break
                else:
                    successful = False
            
            if not successful:
                self.logger.error("Could not send command to device.")
                return False

        return True
    
    def setkHz(self, val, **kwargs):
        """
        Sets the oscillator frequency in kHz.

        Parameters
        ----------
        val: float
            Target frequency in kHz.
        retries: int, default: 3
            Number of retransimssions in case of failure.

        Returns
        -------
        success: bool
            True if successful, False otherwise.
        """
        return self.setHz(val*1e3, **kwargs)
    
    def setMHz(self, val, **kwargs):
        """
        Sets the oscillator frequency in MHz.

        Parameters
        ----------
        val: float
            Target frequency in MHz.
        retries: int, default: 3
            Number of retransimssions in case of failure.

        Returns
        -------
        success: bool
            True if successful, False otherwise.
        """
        return self.setHz(val*1e6, **kwargs)
    
    def setGHz(self, val, **kwargs):
        """
        Sets the oscillator frequency in GHz.

        Parameters
        ----------
        val: float
            Target frequency in GHz.
        retries: int, default: 3
            Number of retransimssions in case of failure.

        Returns
        -------
        success: bool
            True if successful, False otherwise.
        """
        return self.setHz(val*1e9, **kwargs)
