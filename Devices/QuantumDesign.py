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

import MultiPyVu
import numpy as np
import time
import logging
from IPython.utils.io import capture_output

def oe2apm(oe):
    """
    Converts Oersted units (CGS) to A/m (SI)

    Parameters
    ----------
    oe: float
        H-field strength in Oersted

    Returns
    -------
    apm: float
        H-field strength in A/m
    """
    return oe * 1000 / (4*np.pi)

def apm2oe(apm):
    """
    Converts A/m units (SI) to Oersted (CGS)

    Parameters
    ----------
    apm: float
        H-field strength in A/m

    Returns
    -------
    oe: float
        H-field strength in Oersted
    """
    return apm * (4*np.pi) / 1000

def oe2tesla(oe):
    return oe2apm(oe) * 1.25663706127e-6

def apm2tesla(apm):
    return apm * 1.25663706127e-6

def tesla2apm(tesla):
    return tesla / 1.25663706127e-6

def tesla2oe(tesla):
    return apm2oe(tesla / 1.25663706127e-6)

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

        return temp, rate, fast

    def setField(self, setpoint, rate, mode = "linear", driven = False, si = False):
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
        si: bool, default: False
            Indicates whether the setpoint and rate are given in the CGS (False) or SI (True) unit system.
        """
        with capture_output():
            with MultiPyVu.Client(host=self.addr) as client:
                approachMode = getattr(client.field.approach_mode, mode, None)
                if approachMode is None:
                    self.logger.error(f"The entered mode \"{mode}\" is not valid. Please use one of: \"linear\", \"no_overshoot\" or \"oscillate\"")
                    return

                driveMode = client.field.driven_mode.driven if driven else client.field.driven_mode.persistent

                if si:
                    setpoint = apm2oe(setpoint)
                    rate = apm2oe(setpoint)

                client.set_field(setpoint, rate, approachMode, driveMode)

    def getField(self, si = False):
        """
        Reads back H-field from PPMS.

        Parameters
        ----------
        si: bool, default: False
            Indicates whether the H-field strength should be returned in Oersted (False) or A/m (True).

        Returns
        -------
        field: float
            Current H-field strength in Oersted or A/m.
        status: str
            Status string.
        """
        with capture_output():
            with MultiPyVu.Client(host=self.addr) as client:
                field, status = client.get_field()

                if si:
                    field = oe2apm(field)

        return field, status

    def getFieldSetpoint(self, si = False):
        """
        Reads back H-field setpoint from PPMS.

        Parameters
        ----------
        si: bool, default: False
            Indicates whether the H-field strength should be returned in Oersted (False) or A/m (True)

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


        if si:
            field = oe2apm(field)
            rate = oe2apm(rate)

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

                # TODO: Check if this actually gives back a bool, and add in a call to isSteady if it doesn't.
                return client.wait_for(delay, timeout, tempWait | fieldWait | chamberWait)

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
        """

        if not (temp or field or chamber):
            self.logger.warning("At least one of temp, field or chamber must be enabled.")
            return False

        with capture_output():
            with MultiPyVu.Client(host=self.addr) as client:
                tempWait = client.temperature.waitfor if temp else 0
                fieldWait = client.field.waitfor if field else 0
                chamberWait = client.chamber.waitfor if chamber else 0

                return client.wait_for(tempWait | fieldWait | chamberWait)

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
