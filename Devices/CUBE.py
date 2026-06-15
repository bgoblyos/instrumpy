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

class CUBE():
    """
    Driver class for Coherent CUBE and Sapphire lasers.

    Manages serial communication, state control, and power clamping based on
    hardware limits and user-defined configurations.
    """
    def __init__(self, rm, address, config = "Config/CUBE_limits.csv", maxOverride = None):
        """
        Initializes the laser connection and configures power limits.

        Parameters
        ----------
        rm: pyvisa.ResourceManager
            The VISA resource manager instance.
        address: str
            The VISA resource address for the laser (e.g., 'ASRL3::INSTR').
        config: str, default: "Config/CUBE_limits.csv"
            Path to the CSV configuration file containing user-defined power limits.
        maxOverride: float, optional
            A hard override for the maximum allowed power in mW. Overrides the config file.
        """
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
        """
        Retrieves the operating wavelength of the laser.

        Returns
        -------
        wavelength: float
            Laser wavelength in nm.
        """
        resp = self.device.query("?WAVE")
        return float(resp.split('=')[1])


    def getMinPower(self):
        """
        Retrieves the hardware minimum power rating.

        Returns
        -------
        min_power: float
            Minimum power in mW.
        """
        resp = self.device.query("?MINLP")
        return float(resp.split('=')[1])

    def getMaxPower(self):
        """
        Retrieves the hardware maximum power rating.

        Returns
        -------
        max_power: float
            Maximum power in mW.
        """
        resp = self.device.query("?MAXLP")
        return float(resp.split('=')[1])

    def getHours(self):
        """
        Retrieves the total operating hours of the laser diode.

        Returns
        -------
        hours: float
            Operating time in hours.
        """
        resp = self.device.query("?HH")
        return float(resp.split('=')[1])

    def getID(self):
        """
        Retrieves the hardware identification string.

        Returns
        -------
        id: str
            The hardware ID with spaces replaced by hyphens.
        """
        resp = self.device.query("?HID")
        return resp.replace(' ', '-')

    def getServo(self):
        """
        Checks if the laser servo is active.

        Returns
        -------
        servo_active: bool
            True if the servo is active, False otherwise.
        """
        resp = self.device.query("?T")
        return int(resp.split('=')[1]) == 1

    def getSafety(self):
        """
        Checks the safety delay status.

        Returns
        -------
        safety_enabled: bool
            True if the safety delay is enabled.
        """
        resp = self.device.query("?CDRH")
        return int(resp.split('=')[1]) == 1

    def setSafety(self, val : bool):
        """
        Sets the safety delay status.

        Parameters
        ----------
        val: bool
            True to enable the safety delay, False to disable.
        """
        cmd = "CDRH=1" if val else "CDRH=0"
        self.device.query(cmd)

    safety = property(fget=getSafety, fset=setSafety)

    def getExternal(self):
        """
        Checks if the laser is in external emission control mode.

        Returns
        -------
        external_control: bool
            True if external control is enabled.
        """
        resp = self.device.query("?EXT")
        return int(resp.split('=')[1]) == 1

    def getState(self):
        """
        Retrieves the current emission state of the laser.

        Returns
        -------
        state: bool
            True if the laser is emitting (on), False otherwise.
        """
        resp = self.device.query("?L")
        return int(resp.split('=')[1]) == 1

    def on(self, blocking = True):
        """
        Turns the laser emission on.

        Parameters
        ----------
        blocking: bool, default: True
            If True, blocks execution until the laser confirms it is on.
        """
        self.setState(True, blocking=blocking)

    def off(self, blocking = True):
        """
        Turns the laser emission off.

        Parameters
        ----------
        blocking: bool, default: True
            If True, blocks execution until the laser confirms it is off.
        """
        self.setState(False, blocking=blocking)

    def setState(self, state, blocking = True):
        """
        Sets the laser emission state.

        Parameters
        ----------
        state: bool
            True to turn on, False to turn off.
        blocking: bool, default: True
            If True, blocks execution until the laser reaches the target state.
        """
        cmd = "L=1" if state else "L=0"
        self.device.query(cmd)
        if blocking:
            while state ^ self.getState():
                time.sleep(0.1)

    def getPowerSetpoint(self):
        """
        Retrieves the configured power setpoint.

        Returns
        -------
        setpoint: float
            Target power setpoint in mW.
        """
        resp = self.device.query("?SP")
        return float(resp.split('=')[1])

    def getPower(self):
        """
        Retrieves the current measured output power.

        Returns
        -------
        power: float
            Current output power in mW.
        """
        resp = self.device.query("?P")
        return float(resp.split('=')[1])

    def setPower(self, target):
        """
        Sets the output power of the laser.

        Limits the target power based on hardware specifications and user configurations.

        Parameters
        ----------
        target: float
            Target power in mW.
        """
        if target < 0:
            self.logger.error("Cannot set negative power.")
            return None
        elif target <= self.minPower:
            self.logger.info("Power below minimum level. Laser might not start.")

        if target > self.maxPower:
            self.logger.warning(f"Power exceeds maximum rating. It has been reduced to {self.maxPower} mW.")
            target = self.maxPower

        if (self.userLimit is not None) and (target > self.userLimit):
            self.logger.warning(f"Power exceeds user limit. It has been reduced to {self.userLimit} mW.")
            target = self.userLimit

        cmd = "P=" + "{:.3f}".format(target)
        self.device.query(cmd)

    power = property(fget=getPower, fset=setPower)
