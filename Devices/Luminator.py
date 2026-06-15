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

"""
ORIEL Luminator monochromated light source
"""
class Luminator():
    def __init__(self, rm, address, config = "Config/Luminator_cal.csv"):
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
            self.logger.error("Could not load calibration dataset, assuming identity transfer function.")
            [a, b] = [1.0, 0.0]
        finally:
            self.a = a
            self.b = b

    def internal2actual(self, internal):
        return self.a*internal + self.b

    def actual2internal(self, actual):
        return (actual - self.b)/self.a

    def setWavelength(self, target, convert = True):
        target = self.actual2internal(target) if convert else target
        cmd = "GOWAVE " + "{:.3f}".format(target)
        self.device.write(cmd)

    def getWavelength(self, convert = True):
        result = float(self.device.query("WAVE?"))
        return self.internal2actual(result) if convert else result

    wavelength = property(fget=getWavelength, fset=setWavelength)
