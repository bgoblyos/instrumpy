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

import pyvisa
import time
import pandas as pd
import numpy as np
from tqdm.notebook import tqdm
from Devices.ARIS import ARIS
from Devices.Luminator import Luminator

class LuminatorCalibration():
    def __init__(self, sourceAddr):
        self.rm = pyvisa.ResourceManager()
        self.spec = ARIS()
        self.source = Luminator(self.rm, sourceAddr, None)

    def captureSingle(self, target, speed = 50):
        
        prev = self.source.readWavelength(convert = False)
        self.source.setWavelength(target, convert = False)
        
        # Calculate waiting time based on distance to move and sweep (nm/s)
        time.sleep(np.abs(prev - target)/speed + 0.5)
        
        # Get exposure time from autoexposure
        self.spec.setExposure()
        exposure = self.spec.capture()["exposure_us"]

        # Run it again with 10 averages
        self.spec.setExposure(exposure_us = exposure, average = 10)
        results = self.spec.capture()
        reached = self.source.readWavelength(convert = False)

        peakind = np.argmax(results["spectrum"])
        peakval = results["spectrum"][peakind]
        peakloc = results["wavelengths"][peakind]

        mask = np.array(results["spectrum"]) >= (peakval/2)
        lower = np.min(np.array(results["wavelengths"])[mask])
        upper = np.max(np.array(results["wavelengths"])[mask])
        fwhm = upper - lower

        return {
            "setpoint": reached,
            "peak": peakloc,
            "lower3dB": lower,
            "upper3dB": upper,
            "FWHM": fwhm,
            "timestamp_unix_ns": time.time_ns(),
        }

    def captureRange(self, start, stop, n, shuffle = False):
        ws = np.linspace(start, stop, n)
        if shuffle:
            np.random.shuffle(ws)

        res = [self.captureSingle(w) for w in tqdm(ws)]
        return pd.DataFrame.from_dict(res)
