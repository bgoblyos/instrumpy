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

# TODO: unfuck logger after every call
# TODO: use static methods for all the enums

import MultiPyVu
import numpy as np
import time
import logging
import sys
from IPython.utils.io import capture_output

from Utilities.SetupLogging import unfuckLogger

mu0 = 1.25663706127e-6 # in SI units

oeConversion = {
    'oe': 1.0,
    'oersted': 1.0,
    'apm': 1000 / (4*np.pi),
    'a/m': 1000 / (4*np.pi),
    't': mu0 * 1000 / (4*np.pi),
    'tesla': 1.25663706127e-6 * 1000 / (4*np.pi),
}

class PPMS():
    """
    Driver class for Quantum Design PPMS systems.

    This class implements the client only. If you want to run this
    on the same machine MultiVu is running on, make sure to start the
    server manually (python -m MultiPyVu) and use 127.0.0.1 as the
    address given to the client.
    """

    def __init__(self, address):
        """
        Initializes the PPMS connection.

        Parameters
        ----------
        address : str
            The IP address of the server.
        """

        # Set up logger
        self.logger = logging.getLogger('instrumpy.PPMS')
        self.logger.propagate = True
        self.logger.setLevel(logging.NOTSET)
        self.logger.debug("Logger initialized.")

        self.addr = address

    def convertMagUnits(self, value, startingUnit, targetUnit):
        """
        Magnetic unit conversion.

        Parameters
        ----------
        value: float
            Numerical value to be converted.
        startingUnit: str
            Unit in which the value is specified. One of "Oe", "A/m" or "T".
        targetUnit: str
            Unit to which the value should be converted. One of "Oe", "A/m" or "T".
        
        Returns
        -------
        converted: float
            The converted value.
        """
        startingUnit = startingUnit.lower()
        targetUnit = targetUnit.lower()

        if startingUnit not in oeConversion:
            self.logger.error(f'Starting unit \"{startingUnit}\" is not recognized, result may be NaN. Please use \"Oe\", \"A/m\" or \"T\"')
        
        if targetUnit not in oeConversion:
            self.logger.error(f'Target unit \"{targetUnit}\" is not recognized, result may be NaN. Please use \"Oe\", \"A/m\" or \"T\"')

        factor = oeConversion.get(targetUnit, float('nan')) / oeConversion.get(startingUnit, float('nan'))
        return value * factor

    def setTemperature(self, setpoint : float, rate = 10.0, fast = False):
        """
        Sets the temperature of the cryostat.

        Parameters
        ----------
        setpoint: float
            Setpoint temperature in Kelvin.
        rate: float, default: 10
            Approach rate in Kelvin per minute.
        fast: bool, default: False
            Whether to enable fast settle mode. If false, the no overshoot approach mode will be used.
        """
        with capture_output():
            with MultiPyVu.Client(host=self.addr) as client:
                mode = client.temperature.approach_mode.fast_settle if fast else client.temperature.approach_mode.no_overshoot
                client.set_temperature(setpoint, rate, mode)

        unfuckLogger()

    def getTemperature(self):
        """
        Reads back cryostat temperature from PPMS.

        Returns
        -------
        temp: float
            Current cryostat temperature in Kelvin.
        status: str
            Status string.
        """
        with capture_output():
            with MultiPyVu.Client(host=self.addr) as client:
                temp, status = client.get_temperature()
        
        unfuckLogger()
        return temp, status

    def getTemperatureSetpoint(self):
        """
        Reads back cryostat temperature setpoint from PPMS.

        Returns
        -------
        temp: float
            Current cryostat temperature in Kelvin.
        rate: float
            Cryostat approach rate in Kelvin per minute.
        fast: bool
            Whether fast settle mode is enabled. False corresponds to the no overshoot method.
        """
        with capture_output():
            with MultiPyVu.Client(host=self.addr) as client:
                temp, rate, approach = client.get_temperature_setpoints()
                fast = approach == client.temperature.approach_mode.fast_settle

        unfuckLogger()
        return temp, rate, fast

    def setField(self, setpoint, rate, mode = "linear", driven = False, unit = 'T'):
        """
        Sets magnetic field inside the PPMS.

        Parameters
        ----------
        setpoint: float
            Target H-field strength in Oersted (or A/m if si = True).
        rate: float
            Approach rate in Oersted per second (or A/m/s if si = True).
        mode: str, default: "linear"
            Approach mode. Possible values are: "linear", "no_overshoot" or "oscillate".
        driven: bool, default: False
            Sets whether or not the magnet should be in driven mode. False corresponds to persistent mode.
        unit: str, default: 'T'
            Indicates the units in which the setpoint is given. One of "Oe", "A/m" or "T".
        """
        approachMode = getattr(MultiPyVu.Client.field.approach_mode, mode, None)
        if approachMode is None:
            self.logger.error(f"The entered mode \"{mode}\" is not valid. Please use one of: \"linear\", \"no_overshoot\" or \"oscillate\"")
            return
                    
        with capture_output():
            with MultiPyVu.Client(host=self.addr) as client:
                driveMode = client.field.driven_mode.driven if driven else client.field.driven_mode.persistent

                setpoint = self.convertMagUnits(setpoint, startingUnit=unit, targetUnit='Oe')
                rate = self.convertMagUnits(rate, startingUnit=unit, targetUnit='Oe')

                client.set_field(setpoint, rate, approachMode, driveMode)

        unfuckLogger()

    def getField(self, unit = 'T'):
        """
        Reads back the magnetic field from the PPMS.

        Parameters
        ----------
        unit: str, default: 'T'
            Indicates the units in which the response should be given. One of "Oe", "A/m" or "T".

        Returns
        -------
        field: float
            Current magnetic field strength in the selected units.
        status: str
            Status string.
        """
        with capture_output():
            with MultiPyVu.Client(host=self.addr) as client:
                field, status = client.get_field()

        unfuckLogger()
        field = self.convertMagUnits(field, startingUnit='Oe', targetUnit=unit)
        return field, status

    def getFieldSetpoint(self, unit = 'T'):
        """
        Reads back magnetic field setpoint from PPMS.

        Parameters
        ----------
        unit: str, default: 'T'
            Indicates the units in which the response should be given. One of "Oe", "A/m" or "T".

        Returns
        -------
        setpoint: float
            Target H-field strength in Oersted (or A/m if si = True).
        rate: float
            Approach rate in Oersted per second (or A/m/s if si = True).
        mode: str, default: "linear"
            Approach mode. Possible values are: "linear", "no_overshoot" or "oscillate".
        driven: bool, default: False
            Whether or not the magnet is in driven mode. False corresponds to persistent mode.
        """
        with capture_output():
            with MultiPyVu.Client(host=self.addr) as client:
                field, rate, approach, driven = client.get_field_setpoints()

        unfuckLogger()
        field = self.convertMagUnits(field, startingUnit='Oe', targetUnit=unit)
        rate = self.convertMagUnits(rate, startingUnit='Oe', targetUnit=unit)
        driven = driven == "driven"
        
        return field, rate, approach, driven

    def setChamber(self, state):
        """
        Sets the PPMS chamber state.

        Parameters
        ----------
        state: str
            Chamber state. Possible values are: "seal", "purge_seal", "vent_seal", "pump_continuous", "vent_continous" or "high_vacuum".
        """
        with capture_output():
            with MultiPyVu.Client(host=self.addr) as client:
                mode = getattr(client.chamber.mode, state, None)
                if mode is None:
                    self.logger.error(f"The entered state \"{mode}\" is not valid. Please use one of: \"seal\", \"purge_seal\", \"vent_seal\", \"pump_continuous\", \"vent_continous\" or \"high_vacuum\"")
                    return

                client.set_chamber(mode)

    def getChamber(self):
        """
        Gets the PPMS chamber state.

        Returns
        -------
        state: str
            Chamber state. Note: not the same values that are used for setChamber().
        """

        with capture_output():
            with MultiPyVu.Client(host=self.addr) as client:
                resp = client.get_chamber()

        return resp

    def waitFor(self, timeout = 120, delay = 0, temp = False, field = False, chamber = False):
        """
        Wait for setpoints to be reached.

        Parameters
        ----------
        timeout: int, default: 120
            Time in seconds after which the command will return even if the setpoit is not reached.
        delay: int, default: 0
            Time in seconds to wait after all setpoits have been reached. Useful for letting the sample thermalize.
        temp: bool, default: False
            Whether or not to wait for temperature setpoint.
        field: bool, default: False
            Whether or not to wait for H-field setpoint.
        chamber: bool, default: False
            Whether or not to wait for the chamber to complete its current operation.

        Returns
        -------
        result: bool
            Whether or not the setpoit was reached before the timeout.
        """

        if not (temp or field or chamber):
            self.logger.warning("At least one of temp, field or chamber must be enabled.")
            return False

        with capture_output():
            with MultiPyVu.Client(host=self.addr) as client:
                tempWait = client.temperature.waitfor if temp else 0
                fieldWait = client.field.waitfor if field else 0
                chamberWait = client.chamber.waitfor if chamber else 0

                client.wait_for(delay, timeout, tempWait | fieldWait | chamberWait)

        return self.isSteady(temp = temp, field = field, chamber = chamber)

    def isSteady(self, temp = False, field = False, chamber = False):
        """
        Check whether the setpoits have been reached.

        Parameters
        ----------
        temp: bool, default: False
            Whether or not to check for if temperature is in a steady state.
        field: bool, default: False
            Whether or not to check if H-field setpoint has been reached.
        chamber: bool, default: False
            Whether or not to check if the chamber has completes its last operation.

        Returns
        -------
        result: bool
            Whether or not the system is in a steady state.
        """
        
        if not (temp or field or chamber):
            self.logger.warning("At least one of temp, field or chamber must be enabled.")
            return False

        with capture_output():
            with MultiPyVu.Client(host=self.addr) as client:
                tempWait = client.temperature.waitfor if temp else 0
                fieldWait = client.field.waitfor if field else 0
                chamberWait = client.chamber.waitfor if chamber else 0
        
                res = client.is_steady(tempWait | fieldWait | chamberWait)

        unfuckLogger()
        
        if res is not None:
            return res
        else:
            return False

    def setupBridge(self, bridge, channelOn, currentLimit, powerLimit, voltageLimit, delay = 5.0):
        """
        Set up bridge for resistivity measurement

        Parameters
        ----------
        bridge: int
            Number of the target bridge.
        channelOn: bool
            Whether or not to enable the selected bridge.
        currentLimit: float
            Current limit in uA.
        powerLimit: float
            Power limit in uW.
        voltageLimit: float
            Voltage limit in mV.
        delay: float, default: 5.0
            Number of seconds to wait after sending the configuration.
            This allows the module to configure itself before a measurement is taken.
        """
        with capture_output():
            with MultiPyVu.Client(host=self.addr) as client:
                client.resistivity.bridge_setup(
                    bridge_number = bridge,
                    channel_on = channelOn,
                    current_limit_uA = currentLimit,
                    power_limit_uW = powerLimit,
                    voltage_limit_mV = voltageLimit
                )

        time.sleep(delay)

    def setCC(self, bridge, current):
        """
        Set up bridge to output a constant current.

        Parameters
        ----------
        bridge: int
            Number of the target bridge.
        current: float
            Constant current in uA.
        """
        with capture_output():
            with MultiPyVu.Client(host=self.addr) as client:
                client.resistivity.set_current(bridge_number, current)

    def getResistance(self, bridge : int):
        """
        Measure resistance with the given bridge.

        Parameters
        ----------
        bridge: int
            Number of the target bridge.

        Returns
        -------
        res: float
            Measured resistance, presumably in Ohms.
        """

        with capture_output():
            with MultiPyVu.Client(host=self.addr) as client:
                return client.resistivity.get_resistance(bridge)

    def getCurrent(self, bridge : int):
        """
        Measure current on the given bridge.

        Parameters
        ----------
        bridge: int
            Number of the target bridge.

        Returns
        -------
        current: float
            Measured current, presumably in uA.
        """

        with capture_output():
            with MultiPyVu.Client(host=self.addr) as client:
                return client.resistivity.get_current(bridge)

    def setRotatorPosition(self, position : float, rate = 100.0):
        """
        Set the horizontal rotator's position.

        Parameters
        ----------
        position: float
            Rotator position in degrees.
        rate: float, default: 100
            Roation speed in degrees per second.
        """
        with capture_output():
            with MultiPyVu.Client(host=self.addr) as client:
                client.set_position(position, rate)

    def getRotatorPosition(self):
        """
        Reads back rotator position from PPMS.

        Returns
        -------
        position: float
            Current rotator position in degrees.
        status: str
            Status string.
        """
        with capture_output():
            with MultiPyVu.Client(host=self.addr) as client:
                return client.get_position()
