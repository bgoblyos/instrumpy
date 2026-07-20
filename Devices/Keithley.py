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
This module contains the SourceMeter2400 class for interacting with Keithley 2400 SourceMeter series devices.
Current functionality focuses on using it as a source only, so 4-wire mode is not implemented yet.

Examples
--------
Below is a minimum working example showing how to use a Keithley 2400 series SourceMeter.

.. code-block:: python

    import pyvisa
    from Devices.Keithley import SourceMeter2400

    rm = pyvisa.ResourceManager()
    # Automatically find device based on serial number.
    # A matching USB device will be used if it's found.'
    # Otherwise, the hostname defined in the config is used to connect over the network.
    sm = SourceMeter2400(rm, sn='04085563')

    # Set the device to constant current mode at 100 uA with a voltage limit of 1 V
    sm.setCC(100e-6, 1)

    # Read back current and voltage
    print("Current: {sm.I*1e6} uA")
    print("Voltage: {sm.V*1e3} mV")

"""

from pathlib import Path
import logging
import json
import time
import sys

if "sphinx" in sys.modules:
    PROJECT_ROOT = Path(".")
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]

class SourceMeter2400():
    """
    Driver class for Keithley 2400 SourceMeter series devices.
    """
    def __init__(self, rm, sn = None, addressOverride=None, config = (PROJECT_ROOT / "Config" / "SourceMeter.json")):
        """
        Parameters
        ----------
        rm: pyvisa.ResourceManager
            Resource manager instance with which to open the instrument
        sn: str, optional
            Serial number of the instrument. Used for grabbing the hostname from the config or finding the USB device.
            If this is None, addressOverride should be specified.
        addressOverride: str, optional
            Manually specified VISA resource locator. Overrides sn.
            If this is None, sn should be specified.
        config: pathlib.Path, default: "Config/SourceMeter.json"
            Config file path.
        """
        self.logger = logging.getLogger('instrumpy.SourceMeter2400')
        self.logger.propagate = True
        self.logger.setLevel(logging.NOTSET)
        self.logger.debug("Logger initialized.")

        self.config = config

        self.addr = None
        if addressOverride is not None:
            self.addr = addressOverride
        elif sn is not None:
            # try USB
            candidates = rm.list_resources(f'?*{sn}?*::INSTR')
            if len(candidates) >= 1:
                if len(candidates) > 1:
                    self.logger.warning(f'Multiple instruments found ({candidates}), picking first option.')

                self.addr = candidates[0]
            elif config is not None:
                # try TCPIP
                try:
                    with open(config, "r") as file:
                        d = json.load(file)
                        hostname = d.get('devices', {}).get(sn, {}).get('hostname', None)
                        if hostname is not None:
                            self.addr = f'TCPIP::{hostname}::INSTR'
                        else:
                            self.logger.warning(f'Key devices.{sn}.hostname is not present in the config.')
                            self.addr = None
                except Exception as e:
                    self.logger.warning(f"Configuration could not be loaded: {e}")
                    self.addr = None
        else:
            self.logger.warning(f'Either sn or addressOverride needs to be set.')
            self.addr = None

        if self.addr is not None:
            self.device = rm.open_resource(self.addr)
        else:
            self.device = None
            self.logger.error(f'No valid address could be found, device will not be opened.')

        self.device.read_termination = '\n'

    def beep(self, f, t):
        """
        Plays a beep of the given frequency for the given time.
        Blocks until note is played.

        Parameters
        ----------
        f: float
            Frequency of beep in Hz. Use 0 for silence.
        t: float
            Duration of beep in seconds.
        """
        start = time.time()
        if f > 0:
            self.device.write(f'SYST:BEEP {f}, {t}')

        # wait however long it takes to play the note
        while (time.time() - start) < t:
            pass

    def chime(self, name):
        """
        Plays a chime defined in the config file.
        See the 'chimes' key of the config.

        Parameters
        ----------
        name: str
            Name of chime in the config file.
        """
        if self.config is None:
            self.logger.warning('Config file is not defined, cannot find predefined chimes')
            return

        chime = []
        try:
            with open(self.config, "r") as file:
                d = json.load(file)
                chime = d.get('chimes', {}).get(name, [])

        except Exception as e:
                    self.logger.warning(f"Configuration could not be loaded: {e}")
                    return

        if len(chime) == 0:
            self.logger.warning(f"Chime could not be loaded, check that the chimes.{name} key exists.")
            return

        for note in chime:
            self.beep(
                note.get('f', 0),
                note.get('t', 0)
            )

    # Output toggle
    def getOutput(self):
        """
        Get the output state.

        Returns
        -------
        output: bool
            If True, the outputs are enabled.
            If False, the outputs are disabled.
        """
        resp = self.device.query('OUTP:STAT?')
        return int(resp) == 1

    def setOutput(self, output):
        """
        Set the output state.

        Parameters
        ----------
        output: bool
            If True, the outputs are enabled.
            If False, the outputs are disabled.
        """
        cmd = f'OUTP:STAT {'1' if output else '0'}'
        self.device.write(cmd)

    #: bool: Gets or sets whther the output is active.
    output = property(fget=getOutput, fset=setOutput)

    def on(self):
        """
        Turns the ouptut on.
        """
        self.setOutput(True)

    def off(self):
        """
        Turns the ouptut off.
        """
        self.setOutput(False)

    # Select front or back terminals
    def getFront(self):
        """
        Get the front panel ports as active.

        Returns
        ----------
        front: bool
            If True, the front panel ports are active.
            If False, the back panel ports are active.
        """
        resp = self.device.query('ROUT:TERM?')
        return resp == 'FRON'

    def setFront(front = True):
        """
        Set the front panel ports as active.

        Parameters
        ----------
        front: bool, default: True
            If True, the front panel ports are active.
            If False, the back panel ports are active.
        """
        cmd = f'ROUT:TERM {'FRON' if front else 'REAR'}'
        self.device.write(cmd)

    #: bool: Gets or sets the active status of the front panel ports. True corresponds to the front, while False means back panel.
    front = property(fget=getFront, fset=setFront)

    # CV and CC modes
    def setCV(self, V, I_lim = None):
        """
        Set the device to constant voltage mode.

        Parameters
        ----------
        V: float
            Target voltage in volts.
        I_lim: float, optional
            Current limit in amperes.
        """
        self.device.write('SOUR:FUNC VOLT')
        self.device.write(f'SOUR:VOLT {V}')
        if I_lim is not None:
            self.device.write(f'SOUR:VOLT:ILIM {I_lim}')

    def setCC(self, I, V_lim = None):
        """
        Set the device to constant current mode.

        Parameters
        ----------
        I: float
            Target current in amperes.
        V_lim: float, optional
            Voltage limit in volts.
        """
        self.device.write('SOUR:FUNC CURR')
        self.device.write(f'SOUR:CURR {I}')
        if V_lim is not None:
            self.device.write(f'SOUR:CURR:VLIM {V_lim}')

    def getV(self):
        return float(self.device.query('MEAS:VOLT?'))

    #: float: Measure voltage in volts on the force or sense pins depending on mode.
    V = property(fget=getV)

    def getI(self):
        return float(self.device.query('MEAS:CURR?'))

    #: float: Measure current in amperes on the force or sense pins depending on mode.
    I = property(fget=getI)

    def getR(self):
        return float(self.device.query('MEAS:RES?'))

    #: float: Measure resistance in Ohms in 2 or 4-point configuration depending on mode.
    R = property(fget=getR)
