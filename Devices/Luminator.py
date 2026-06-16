"""
Copyright (C) 2026 Bence Göblyös

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, version 3.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see https://www.gnu.org/licenses/.
"""

import numpy as np
import pandas as pd
import logging

PROJECT_ROOT = Path(__file__).resolve().parents[1]

class Luminator():
    """
    Driver class for the ORIEL Luminator monochromated light source.

    Handles instrument communication via PyVISA and applies an optional
    linear wavelength calibration based on a provided configuration file.
    """
    def __init__(self, rm, address, config = (PROJECT_ROOT / "Config" / "Luminator.csv")):
        """
        Initializes the monochromator connection and loads calibration data.

        Parameters
        ----------
        rm: pyvisa.ResourceManager
            The VISA resource manager instance.
        address: str
            The VISA resource address for the device.
        config: str, default: "Config/Luminator_cal.csv"
            Path to the CSV configuration file containing calibration data
            with 'setpoint' and 'peak' columns.
        """
        # Set up logger
        self.logger = logging.getLogger('instrumpy.Luminator')
        self.logger.propagate = True
        self.logger.setLevel(logging.NOTSET)
        self.logger.debug("Logger initialized.")

        self.device = rm.open_resource(address)
        self.device.write_termination = "\r\n"
        self.device.read_termination = "\r\n"

        try:
            df = pd.read_csv(config)
            [a, b] = np.polyfit(df.setpoint, df.peak, 1)
        except:
            self.logger.warning("Could not load calibration dataset, assuming identity transfer function.")
            [a, b] = [1.0, 0.0]
        finally:
            self.a = a
            self.b = b

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
        return self.a*internal + self.b

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
        return (actual - self.b)/self.a

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
        target = self.actual2internal(target) if convert else target
        cmd = "GOWAVE " + "{:.3f}".format(target)
        self.device.write(cmd)

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

    wavelength = property(fget=getWavelength, fset=setWavelength)
