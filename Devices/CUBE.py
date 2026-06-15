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

import logging
import time
import pandas as pd

"""
Coherent CUBE laser
"""
class CUBE():
    def __init__(self, rm, address, config = "Config/CUBE_limits.csv", maxOverride = None):
        # Set up logger
        self.logger = logging.getLogger('instrumpy.CUBE')
        self.logger.propagate = True
        self.logger.setLevel(logging.NOTSET)
        self.logger.debug("Logger initialized.")

        # Set up serial communication
        self.device = rm.open_resource(address)
        self.device.baud_rate = 19200
        self.device.write_termination = "\r\n"
        self.device.read_termination = "\r\n"

        # Set up power clamping
        self.maxPower = self.getMaxPower()
        self.minPower = self.getMinPower()
        self.id = self.getID()

        if maxOverride is not None:
            self.userLimit = maxOverride
        else:
            try:
                df = pd.read_csv(config)
                mask = df.serial == self.id
                if len(mask) > 1:
                    self.logger.warning("Duplicate config entry found. Using first match.")
                lim = df.limit[mask][0]
            except:
                self.logger.error("Could not load limits, user limiting is disabled.")
                lim = None
            finally:
                self.userLimit = lim
        

    def getWavelength(self):
        resp = self.device.query("?WAVE")
        return float(resp.split('=')[1])


    def getMinPower(self):
        resp = self.device.query("?MINLP")
        return float(resp.split('=')[1])

    def getMaxPower(self):
        resp = self.device.query("?MAXLP")
        return float(resp.split('=')[1])

    def getHours(self):
        resp = self.device.query("?HH")
        return float(resp.split('=')[1])

    def getID(self):
        resp = self.device.query("?HID")
        return resp.replace(' ', '-')
        
    def getServo(self):
        resp = self.device.query("?T")
        return int(resp.split('=')[1]) == 1

    def getSafety(self):
        resp = self.device.query("?CDRH")
        return int(resp.split('=')[1]) == 1

    def setSafety(self, val : bool):
        cmd = "CDRH=1" if val else "CDRH=0"
        self.device.query(cmd)

    safety = property(fget=getSafety, fset=setSafety)

    def getExternal(self):
        resp = self.device.query("?EXT")
        return int(resp.split('=')[1]) == 1

    def getState(self):
        resp = self.device.query("?L")
        return int(resp.split('=')[1]) == 1
        
    def on(self, blocking = True):
        self.setState(True, blocking=blocking)

    def off(self, blocking = True):
        self.setState(False, blocking=blocking)

    def setState(self, state, blocking = True):
        cmd = "L=1" if state else "L=0"
        self.device.query(cmd)
        if blocking:
            while state ^ self.getState():
                time.sleep(0.1)

    def getPowerSetpoint(self):
        resp = self.device.query("?SP")
        return float(resp.split('=')[1])

    def getPower(self):
        resp = self.device.query("?P")
        return float(resp.split('=')[1])

    def setPower(self, target, feedbackDelay=0.25):
        if target < 0:
            self.logger.error("Cannot set negative power")
            return None
        elif target <= self.minPower:
            self.logger.info("Power below minimum level. Laser might not start.")

        if target > self.maxPower:
            self.logger.warning(f"Power exceeds maximum rating. It has been reduced to {self.maxPower} mW")
            target = self.maxPower

        if (self.userLimit is not None) and (target > self.userLimit):
            self.logger.warning(f"Power exceeds user limit. It has been reduced to {self.userLimit} mW")
            target = self.userLimit
            
        cmd = "P=" + "{:.3f}".format(target)
        self.device.query(cmd)
        time.sleep(feedbackDelay)
        return self.getPower()

    power = property(fget=getPower, fset=setPower)

    
        
