"""
Copyright (C) 2025 Bence Göblyös

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, version 3.
"""

import logging
import time
import json

class CoherentLaser():
    """
    Parent driver class for Coherent lasers.
    Handles the common API commands and limits.
    """
    def __init__(self, rm, address, config="Config/Coherent.json", maxOverride=None):
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
        self.logger = logging.getLogger(f'instrumpy.{self.__class__.__name__}')
        self.logger.propagate = True
        self.logger.setLevel(logging.NOTSET)
        self.logger.debug("Logger initialized.")

        # Set up serial communication
        self.device = rm.open_resource(address)
        self.device.baud_rate = 19200
        self.device.write_termination = "\r\n"
        self.device.read_termination = "\r\n"

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
        raise NotImplementedError("Subclasses must implement custom write logic.")

    def query(self, cmd):
        raise NotImplementedError("Subclasses must implement custom query logic.")

    def getID(self):
        raise NotImplementedError("Subclasses must implement custom query logic.")

    def getWavelength(self):
        resp = self.query("?WAVE")
        return float(resp.split('=')[1])

    def getMinPower(self):
        resp = self.query("?MINLP")
        return float(resp.split('=')[1])

    def getMaxPower(self):
        resp = self.query("?MAXLP")
        return float(resp.split('=')[1])

    def getHours(self):
        resp = self.query("?HH")
        return float(resp.split('=')[1])

    def getServo(self):
        resp = self.query("?T")
        return int(resp.split('=')[1]) == 1

    def getSafety(self):
        resp = self.query("?CDRH")
        return int(resp.split('=')[1]) == 1

    def setSafety(self, val: bool):
        cmd = "CDRH=1" if val else "CDRH=0"
        self.write(cmd)

    safety = property(fget=getSafety, fset=setSafety)

    def getExternal(self):
        resp = self.query("?EXT")
        return int(resp.split('=')[1]) == 1

    def getState(self):
        resp = self.query("?L")
        return int(resp.split('=')[1]) == 1

    def on(self, blocking=True):
        self.setState(True, blocking=blocking)

    def off(self, blocking=True):
        self.setState(False, blocking=blocking)

    def setState(self, state, blocking=True):
        cmd = "L=1" if state else "L=0"
        self.write(cmd)
        if blocking:
            while state ^ self.getState():
                time.sleep(0.1)

    def getPowerSetpoint(self):
        resp = self.query("?SP")
        return float(resp.split('=')[1])

    def getPower(self):
        resp = self.query("?P")
        return float(resp.split('=')[1])

    def setPower(self, target):
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
        self.write(cmd)

    power = property(fget=getPower, fset=setPower)


class CUBE(CoherentLaser):
    """
    Driver class for Coherent CUBE lasers.
    """
    def write(self, cmd):
        # Maintain original logic: CUBE returns a prompt (\r\n) after write
        # commands, which pyvisa's query() handles by reading and discarding.
        self.device.query(cmd)

    def query(self, cmd):
        return self.device.query(cmd)

    def getID(self):
        resp = self.query("?HID")
        return resp.replace(' ', '-')


class SapphireLP(CoherentLaser):
    """
    Driver class for Coherent Sapphire LP lasers.
    Includes custom buffer clearing to account for non-disableable command echo.
    """
    def write(self, cmd):
        self.device.write(cmd)
        # Read back the echoed command from the buffer to prevent
        # it from polluting the next query
        self.device.read()

    def query(self, cmd):
        self.device.write(cmd)
        self.device.read()        # Discard the command echo
        return self.device.read() # Return the actual laser response

    def getID(self):
        resp = self.query("?HID")
        return str(round(resp))
