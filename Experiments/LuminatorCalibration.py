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
        self.rm = pyvisa.resourceManager()
        self.spec = ARIS()
        self.source = Luminator(self.rm, sourceAddr, None)

    def captureSingle(self, target):
        self.source.setWavelegth(target, transform = False)
        time.sleep(3) # Wait a few seconds for it to move
        
        # Get exposure time from autoexposure
        self.spec.setExposure()
        exposure = self.spec.capture()["exposure_us"]

        # Run it again with 10 averages
        self.spec.setExposure(exposure_us = exposure, average = 10)
        results = self.spec.capture()
        reached = self.source.readWavelength(transform = False)

        peakind = np.argmax(results["spectrum"])
        peakval = results["spectrum"][peakind]
        peakloc = results["wavelengths"][peakind]

        mask = results["spectrum"] <= peakval
        lower = np.minimum(results["wavelength"][mask])
        upper = np.maximum(results["wavelength"][mask])
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