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
import json

PROJECT_ROOT = Path(__file__).resolve().parents[1]

class PM100():
    """
    Driver class for ThorLabs PM100x power meter head units.

    Manages instrument communication via PyVISA and applies an optional
    polynomial wavelength-dependent attenuation calibration. Provides explicit
    getters and property accessors for core SCPI functionality.
    """
    def __init__(self, rm, address, attName=None, attConfig=(PROJECT_ROOT / "Config" / "PM100.json")):
        """
        Initializes the power meter connection and loads optional calibration data.

        Parameters
        ----------
        rm : pyvisa.ResourceManager
            The VISA resource manager instance.
        address : str
            The VISA resource address for the device.
        attName : str, optional
            The key inside the JSON configuration file corresponding to the
            desired attenuation profile. Up to 9th order polynomials are accepted.
        attConfig : str, default: "Config/PM100_attenuation.json"
            Path to the JSON configuration file containing polynomial coefficients
            for external attenuation/gain adjustments.
        """
        # Set up logger
        self.logger = logging.getLogger('instrumpy.PM100')
        self.logger.propagate = True
        self.logger.setLevel(logging.NOTSET)
        self.logger.debug("Logger initialized.")

        self.device = rm.open_resource(address)
        self.device.read_termination = "\n"

        self.setUnits('W')

        self.poly = None
        self.lower = 0
        self.upper = 0
        if attConfig is not None and attName is not None:
            try:
                with open(attConfig, "r") as file:
                    d = json.load(file)[attName]

                coeffs = []
                for i in range(10):
                    k = f'c{i}'
                    if k in d:
                        coeffs.append(d[k])

                self.lower = d.get("cal_lower", 0)
                self.upper = d.get("cal_upper", 0)
                self.poly = np.polynomial.Polynomial(coeffs)

            except Exception as e:
                self.logger.warning(f"Configuration could not be loaded: {e}")

    def getID(self):
        """
        Returns the instrument identification string.

        Returns
        -------
        idn : str
            Identification string (manufacturer, model, serial, firmware).
        """
        return self.device.query("*IDN?")

    def getSensorID(self):
        """
        Returns the connected sensor identification string.

        Returns
        -------
        info : str
            Sensor identification and configuration information.
        """
        return self.device.query("SYST:SENS:IDN?")

    def getError(self):
        """
        Returns the latest error code and message from the error queue.

        Returns
        -------
        error : str
            Formatted error message.
        """
        return self.device.query("SYST:ERR?")

    def zero(self):
        """
        Initiates zero adjustment (non-blocking).
        """
        self.logger.info("Starting zero adjustment.")
        self.device.write("SENS:CORR:COLL:ZERO:INIT")

    def getWavelength(self):
        """
        Returns current operation wavelength.

        Returns
        -------
        wavelength : float
            Current wavelength in nm.
        """
        return float(self.device.query("SENS:CORR:WAV?"))

    def setWavelength(self, val):
        """
        Sets operation wavelength.

        Parameters
        ----------
        val : float
            Wavelength in nm.
        """
        if self.poly is not None and convert:
-            if self.lower != 0 and val < self.lower:
-                self.logger.warning(f"The set wavelength ({val} nm) is below the calibrated minimum ({self.lower} nm). Attenuation calculations may be erroneous.")
-            if self.upper != 0 and val > self.upper:
-                self.logger.warning(f"The set wavelength ({val} nm) is above the calibrated maximum ({self.upper} nm). Attenuation calculations may be erroneous.")
        self.device.write(f"SENS:CORR:WAV {int(val)}")

    wavelength = property(fget=getWavelength, fset=setWavelength)

    def getAverage(self):
        """
        Returns the number of samples averaged.

        Returns
        -------
        count : int
            Number of samples per measurement.
        """
        return int(self.device.query("SENS:AVER:COUN?"))

    def setAverage(self, val):
        """
        Sets the number of samples to average.

        Parameters
        ----------
        val : int
            Number of samples.
        """
        self.device.write(f"SENS:AVER:COUN {int(val)}")

    average = property(fget=getAverage, fset=setAverage)

    def getFilterLowpass(self):
        """
        Returns the state of the low-pass filter.

        Returns
        -------
        enabled : bool
            True if low-pass filter is enabled.
        """
        return int(self.device.query("INP:PDI:FILT:LPAS:STAT?")) == 1

    def setFilterLowpass(self, state: bool):
        """
        Enables or disables the low-pass filter.

        Parameters
        ----------
        state : bool
            True to enable, False to disable.
        """
        self.device.write(f"INP:PDI:FILT:LPAS:STAT {1 if state else 0}")

    filterLowpass = property(fget=getFilterLowpass, fset=setFilterLowpass)

    def getThermopileAccelerator(self):
        """
        Returns the state of the thermopile accelerator.

        Returns
        -------
        active : bool
            True if thermopile accelerator is active.
        """
        return int(self.device.query("INP:THER:ACC:STAT?")) == 1

    def setThermopileAccelerator(self, state: bool):
        """
        Enables or disables the thermopile accelerator.

        Parameters
        ----------
        state : bool
            True to enable, False to disable.
        """
        self.device.write(f"INP:THER:ACC:STAT {1 if state else 0}")

    thermopileAccelerator = property(fget=getThermopileAccelerator, fset=setThermopileAccelerator)

    def setUnits(self, target):
        """
        Sets measurement units.

        Parameters
        ----------
        target : str
            Unit type ('W' or 'DBM').
        """
        self.device.write(f"SENS:POW:UNIT {target}")

    def setAutoRange(self, state=True, mode="POW"):
        """
        Enables or disables auto-ranging for a specific mode.

        Parameters
        ----------
        state : bool, default: True
            True to enable, False to disable.
        mode : str, default: "POW"
            Measurement mode (e.g., "POW", "CURR", "VOLT").
        """
        self.device.write(f"SENS:{mode}:RANG:AUTO {'ON' if state else 'OFF'}")

    def getPower(self, applyCalibration=True):
        """
        Returns measured power.

        Parameters
        ----------
        applyCalibration : bool, default: True
            Whether to apply the loaded polynomial attenuation profile.

        Returns
        -------
        power : float
            Measured optical power.
        """
        raw = float(self.device.query("MEAS:POW?"))
        if self.poly is not None and applyCalibration:
            wl = self.getWavelength()
            return raw * self.poly(wl)
        else:
            return raw

    power = property(fget=getPower)

    def getEnergy(self):
        """
        Returns measured pulse energy.

        Returns
        -------
        energy : float
            Measured pulse energy.
        """
        return float(self.device.query("MEAS:ENER?"))

    energy = property(fget=getEnergy)

    def getFrequency(self):
        """
        Returns measured repetition frequency.

        Returns
        -------
        frequency : float
            Measured frequency in Hz.
        """
        return float(self.device.query("MEAS:FREQ?"))

    frequency = property(fget=getFrequency)

    def getTemperature(self):
        """
        Returns current sensor temperature.

        Returns
        -------
        temp : float
            Temperature in Celsius.
        """
        return float(self.device.query("MEAS:TEMP?"))

    temperature = property(fget=getTemperature)
