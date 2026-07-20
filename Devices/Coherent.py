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
This module contains drivers for Coherent CUBE and Sapphire lasers.
The API for these is identical, only their backends are different.
Simply instantiate the correct class for your laser.
The class ``CoherentLaser`` contains the complete user-facing API,
but it should not be used as it cannot intercafe with anything.

Examples
--------
Below is a minimum working example showing how to use a Coherent CUBE laser.

.. code-block:: python

    import pyvisa
    import time
    from Devices.Coherent import CUBE

    rm = pyvisa.ResourceManager()
    cube = CUBE(rm, 'ASRL3::INSTR') # Assuming the serial link is on COM3

    print(f'Serial number: {cube.getID()}')

    cube.on() # Turn on the laser

    cube.power = 50                          # Set to 50 mW
    time.sleep(5)                            # Wait for it to reach the target
    print(f'Current power: {cube.power} mw') # Read back the power

    cube.off() # Turn off the laser
"""

import logging
import time
import json
import pyvisa
import sys
from pathlib import Path

if "sphinx" in sys.modules:
    PROJECT_ROOT = Path(".")
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]

class CoherentLaser():
    """
    Parent driver class for Coherent lasers.
    Handles the common API commands and limits.
    """
    def __init__(self, rm, address, config=(PROJECT_ROOT / "Config" / "Coherent.json"), maxOverride=None):
        """
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
        self.logger = logging.getLogger(f'instrumpy.{self.__class__.__name__}')
        self.logger.propagate = True
        self.logger.setLevel(logging.NOTSET)
        self.logger.debug("Logger initialized.")

        # Set up serial communication
        self.device = rm.open_resource(address)
        self.device.baud_rate = 19200
        self.device.write_termination = "\r\n"
        self.device.read_termination = "\r\n"

        # Disable prompt
        self.write(">=0")
        self.flushBuffer()

        self.maxPower = self.getMaxPower()
        self.minPower = self.getMinPower()
        self.id = self.getID()

        # Read user limits from config
        self.userLimit = None

        if maxOverride is not None:
            self.userLimit = maxOverride
        else:
            try:
                with open(config, "r") as file:
                    conf = json.load(file)

                entry = conf.get(self.id, None)
                if entry is not None and "limit" in entry:
                    self.userLimit = entry["limit"]
                else:
                    self.logger.warning("Config entry does not contain a limit key or entry is missing. User limits are disabled.")
            except Exception:
                self.logger.warning("Could not open config file. User limits are disabled.")

    def write(self, cmd):
        """
        Send a string to the device.

        Parameters
        ----------
        cmd: str
            The command to be sent to the device.
        """
        raise NotImplementedError("Subclasses must implement custom write logic.")

    def query(self, cmd):
        """
        Send a string to the device and get the response.

        Parameters
        ----------
        cmd: str
            The command to be sent to the device.

        Returns
        -------
        resp: str
            Response to the query.
        """
        raise NotImplementedError("Subclasses must implement custom query logic.")

    def flushBuffer(self):
        """
        Flushes the read queue to prevent issues. Only implemented for Sapphire.
        """
        pass

    def getID(self):
        """
        Get the serial number of the laser head.

        Returns
        -------
        id: str
            Serial number prefixed with the laser type.
        """
        raise NotImplementedError("Subclasses must implement custom query logic.")

    def getWavelength(self):
        resp = self.query("?WAVE")
        return float(resp)

    #: float: Wavelength of the laser.
    wavelength = property(fget=getWavelength)

    def getMinPower(self):
        """
        Get the minimum rated power of the laser.

        Returns
        -------
        min: float
            Minimum power in mW.
        """
        resp = self.query("?MINLP")
        return float(resp)

    def getMaxPower(self):
        """
        Get the maximum rated power of the laser.

        Returns
        -------
        max: float
            Maximum power in mW.
        """
        resp = self.query("?MAXLP")
        return float(resp)

    def getHours(self):
        """
        Get the power-on hours of the laser.

        Returns
        -------
        hours: float
            Numer of operational hours.
        """
        resp = self.query("?HH")
        return float(resp)

    def getServo(self):
        """
        Query whether servo control is enabled (what even is that?)

        Returns
        -------
        servo: bool
            True if servo is enabled, False otherwise.
        """
        resp = self.query("?T")
        return int(resp) == 1

    def _getSafety(self):
        resp = self.query("?CDRH")
        return int(resp) == 1

    def _setSafety(self, val: bool):
        cmd = "CDRH=1" if val else "CDRH=0"
        self.write(cmd)

    #: bool: Sets or gets whether the turn-on safety delay is enabled.
    safety = property(fget=_getSafety, fset=_setSafety)

    def getExternal(self):
        """
        Query whether external modulation is enabled.

        Returns
        -------
        ext: bool
            True if external modulation is enabled, False otherwise.
        """
        resp = self.query("?EXT")
        return int(resp) == 1

    def getState(self):
        """
        Query whether the laser is turned on.

        Returns
        -------
        ext: bool
            True if the laser is on, False otherwise.
        """
        resp = self.query("?L")
        return int(resp) == 1

    def on(self, blocking=True):
        """
        Turn the laser head on. If blocking is enabled, wait for it to actually turn on before returning.

        Parameters
        ----------
        blocking: bool, default: True
            Whether or not to block execution until the laser turns on.
        """
        self.setState(True, blocking=blocking)

    def off(self, blocking=True):
        """
        Turn the laser head off. If blocking is enabled, wait for it to actually turn off before returning.

        Parameters
        ----------
        blocking: bool, default: True
            Whether or not to block execution until the laser turns off.
        """
        self.setState(False, blocking=blocking)

    def setState(self, state, blocking=True):
        """
        Turn the laser head off. If blocking is enabled, wait for it to actually turn off before returning.

        Parameters
        ----------
        state: bool
            Target state of the laser. Use True to turn on and False to turn off.
        blocking: bool, default: True
            Whether or not to block execution until the laser is in the desired state.
        """
        cmd = "L=1" if state else "L=0"
        self.write(cmd)
        if blocking:
            while state ^ self.getState():
                time.sleep(0.1)

    def getPowerSetpoint(self):
        """
        Get the power setpoint of the laser.
        This should read back the value given in the last ``setPower(target)`` call.
        For the actual output power, use ``power`` or ``getPower()``.

        Returns
        -------
        setpoint: bool
            Power setpoint in mW.
        """
        resp = self.query("?SP")
        return float(resp)

    def getPower(self):
        """
        Get the current output power of the laser in mW.

        Returns
        -------
        pow: float
            Current output power in mW.
        """
        resp = self.query("?P")
        return float(resp)

    #: bool: Sets whether or not the given type of laser accepts power settings under its nominal rating.
    allowUnderpower = True
    
    def setPower(self, target):
        """
        Set the power target for the laser.
        Value will be clamped according to laser capabilities and user-defined limits.

        Parameters
        ----------
        target: float
            Target power in mW.
        """
        if target < 0:
            self.logger.error("Cannot set negative power.")
            return None
        elif target < self.minPower:
            if self.allowUnderpower:
                self.logger.info(f"Power below minimum level. Laser might not start.")
            else:
                self.logger.warning(f"Power below minimum level. It has been increased to {self.minPower} mW.")
                target = self.minPower

        if target > self.maxPower:
            self.logger.warning(f"Power exceeds maximum rating. It has been reduced to {self.maxPower} mW.")
            target = self.maxPower

        if (self.userLimit is not None) and (target > self.userLimit):
            self.logger.warning(f"Power exceeds user limit. It has been reduced to {self.userLimit} mW.")
            target = self.userLimit

        cmd = "P=" + "{:.3f}".format(target)
        self.write(cmd)

    #: float: Get or set the laser's output power in mW.
    power = property(fget=getPower, fset=setPower)


class CUBE(CoherentLaser):
    """
    Driver class for Coherent CUBE lasers.

    Please refer to ``CoherentLaser`` on usage.
    """

    allowUnderpower = True
    
    def write(self, cmd):
        # Maintain original logic: CUBE returns a prompt (\r\n) after write
        # commands, which pyvisa's query() handles by reading and discarding.
        self.device.query(cmd)

    def query(self, cmd):
        resp = self.device.query(cmd)
        return resp.split('=')[-1]

    def getID(self):
        resp = self.query("?HID")
        return "CUBE-" + resp.replace(' ', '-')


class SapphireLP(CoherentLaser):
    """
    Driver class for Coherent Sapphire LP lasers.
    Includes custom buffer clearing to account for non-disableable command echo.

    Please refer to ``CoherentLaser`` on usage.
    """

    allowUnderpower = False
    
    def write(self, cmd, retries = 3):
        """
        Send a string to the device.

        Parameters
        ----------
        cmd: str
            The command to be sent to the device.
        retries: float, default: 3
            Number of retries in case of communication failure.
        """
        for i in range(retries + 1):
            try:
                self.device.write(cmd)
                # Read back the echoed command from the buffer to prevent
                # it from polluting the next query
                self.device.read()
                return
            except pyvisa.VisaIOError as err:
                if err.error_code == -1073807253:
                    self.logger.warning(f"Serial communication issue encountered during write, retrying (attempt {i+1}/{retries}).")
                    self.flushBuffer()
                else:
                    raise err

    def query(self, cmd, retries = 3):
        """
        Send a string to the device and get the response.

        Parameters
        ----------
        cmd: str
            The command to be sent to the device.
        retries: float, default: 3
            Number of retries in case of communication failure.

        Returns
        -------
        resp: str
            Response to the query.
        """
        for i in range(retries + 1):
            try:
                self.device.write(cmd)
                self.device.read()
                return self.device.read()
            except pyvisa.VisaIOError as err:
                if err.error_code == -1073807253:
                    self.logger.warning(f"Serial communication issue encountered during query, retrying (attempt {i+1}/{retries+1}).")
                    self.flushBuffer()
                else:
                    raise err
        

    def flushBuffer(self):
        while self.device.bytes_in_buffer > 0:
            try:
                self.device.read()
            except pyvisa.VisaIOError as err:
                if err.error_code == -1073807253:
                    self.logger.warning("Serial communication issue encountered while flushing buffer, retrying.")
                else:
                    raise err
                

    def getID(self):
        resp = self.query("?HID")
        return "Sapphire-LP-" + str(round(float(resp)))
