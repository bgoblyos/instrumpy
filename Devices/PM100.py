"""
Copyright (C) 2025 Bence Göblyös

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

"""
ThorLabs PM100x power meter head unit
"""
class PM100():
    def __init__(self, rm, address, attName = None, attConfig = "Config/PM100_attenuation.json"):
        # Set up logger
        self.logger = logging.getLogger('instrumpy.PM100')
        self.logger.propagate = True
        self.logger.setLevel(logging.NOTSET)
        self.logger.debug("Logger initialized.")
        
        self.device = rm.open_resource(address)
        self.device.read_termination = "\n"

        self.wavelength = self.getWavelength()

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
                
                if "cal_lower" in d:
                    self.lower = d["cal_lower"]

                if "cal_upper" in d:
                    self.upper = d["cal_upper"]
                
                self.poly = np.polynomial.Polynomial(coeffs)
                
            except:
                self.logger.warning("Configuration could not be loaded")
                self.poly = None
                self.lower = 0
                self.upper = 0

    def setWavelength(self, target):
        self.device.write("SENS:CORR:WAV " + str(int(target)))
        self.wavelength = self.getWavelength()

    def getWavelength(self):
        return float(self.device.query("SENS:CORR:WAV?"))

    def setAutoRange(self):
        self.device.write("SENS:RANGE:AUTO ON")

    def setAverage(self, target):
        self.device.write("SENS:AVER:" + str(int(target)))

    def setUnits(self, target):
        self.device.write("SENS:POW:UNIT " + target)

    def getPower(self, convert = True):
        resp = float(self.device.query("MEAS:POW?"))

        if self.poly is not None and convert:
            if self.lower != 0 and self.wavelength < self.lower:
                self.logger.warning(f"The set wavelength ({self.wavelength} nm) is below the calibrated minimum ({self.lower} nm). Attenuation calculations may be erroneous.")
            if self.upper != 0 and self.wavelength > self.upper:
                self.logger.warning(f"The set wavelength ({self.wavelength} nm) is above the calibrated maximum ({self.upper} nm). Attenuation calculations may be erroneous.")

            return resp * self.poly(self.wavelength)
        else:
            return resp