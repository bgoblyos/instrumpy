# Copyright (C) 2026 Bence Göblyös
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
This module contains the driver for ORIEL Luminator monochromated light sources.

Examples
--------
Below is a minimum working example showing how to use the ORIEL Luminator.

.. code-block:: python

    import pyvisa
    from Devices.ORIEL import Luminator

    rm = pyvisa.ResourceManager()
    device = Luminator(rm, 'GPIB0::4::INSTR')


    device.wavelength = 532 # By default, the first-order wavelength calibration is applied
    print(f'Wavelength: {device.wavelength} nm') # Read back actual wavelength

    # The timeout will prevent new commands from being sent while the monochromator is moving
    device.wavelength = 400
    device.wavelength = 900

    # Everything outside the configured bounds in clamped
    device.wavelength = 0
    device.wavelength = 10000
"""


import numpy as np
import json
import logging
import time
import sys
from pathlib import Path

if "sphinx" in sys.modules:
    PROJECT_ROOT = Path(".")
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]

class Luminator():
    """
    Driver class for the ORIEL Luminator monochromated light source.

    Handles instrument communication via PyVISA and applies an optional
    linear wavelength calibration based on a provided configuration file.
    """
    def __init__(self, rm, address, config = (PROJECT_ROOT / "Config" / "Luminator.json")):
        """
        Parameters
        ----------
        rm: pyvisa.ResourceManager
            The VISA resource manager instance.
        address: str
            The VISA resource address for the device.
        config: Path, default: "Config/Luminator.json"
            Path to the JSON configuration file containing calibration data
            with 'c0' and 'c1' coefficients, 'lower' and 'upper' limits and
            'speed' value.
        """

        # Set up logger
        self.logger = logging.getLogger('instrumpy.Luminator')
        self.logger.propagate = True
        self.logger.setLevel(logging.NOTSET)
        self.logger.debug("Logger initialized.")

        self.device = rm.open_resource(address)
        self.device.write_termination = "\r\n"
        self.device.read_termination = "\r\n"

        # TODO: Store multiple config entries and fetch them by serial number.
        d = {}
        if config is not None:
            try:
                with open(config, "r") as file:
                    d = json.load(file)
            except Exception as e:
                self.logger.warning(f"Configuration could not be loaded: {e}")
                d = {}

        self.a = d.get('c1', 1.0)
        self.b = d.get('c0', 0.0)
        self.lower = d.get('lower', 300.0)
        self.upper = d.get('upper', 1200.0)
        self.speed = d.get('speed', 50.0)

    def internal2actual(self, internal):
        """
        Converts the internal monochromator setpoint to the actual output wavelength.

        Parameters
        ----------
        internal: float
            The internal wavelength setpoint in nm.

        Returns
        -------
        actual: float
            The calibrated actual output wavelength in nm.
        """
        return float(self.a*internal + self.b)

    def actual2internal(self, actual):
        """
        Converts a desired actual output wavelength to the required internal setpoint.

        Parameters
        ----------
        actual: float
            The desired actual output wavelength in nm.

        Returns
        -------
        internal: float
            The necessary internal setpoint in nm to achieve the actual wavelength.
        """
        return float((actual - self.b)/self.a)

    def setWavelength(self, target, convert = True):
        """
        Sets the operating wavelength of the monochromator.

        Parameters
        ----------
        target: float
            The target wavelength in nm.
        convert: bool, default: True
            If True, applies the linear calibration to the target before sending.
        """
        old = self.getWavelength(convert = convert)

        if target < self.lower:
            target = self.lower
            self.logger.warning(f"Wavelength below minimum level. It has been increased to {self.lower} nm.")

        if target > self.upper:
            target = self.upper
            self.logger.warning(f"Wavelength above maximum level. It has been decreased to {self.upper} nm.")

        wait = (np.abs(old - target) / self.speed) + 0.05
        target = self.actual2internal(target) if convert else target
        
        cmd = "GOWAVE " + "{:.3f}".format(target)
        self.device.write(cmd)
        time.sleep(wait)

    def getWavelength(self, convert = True):
        """
        Retrieves the current operating wavelength of the monochromator.

        Parameters
        ----------
        convert: bool, default: True
            If True, returns the calibrated actual wavelength.
            If False, returns the raw internal setpoint.

        Returns
        -------
        wavelength: float
            The current wavelength in nm.
        """
        result = float(self.device.query("WAVE?"))
        return self.internal2actual(result) if convert else result

    #: float: Get or set the wavelength of the monochromator in nm. Applies calibration if available.
    wavelength = property(fget=getWavelength, fset=setWavelength)
