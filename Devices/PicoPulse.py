# Copyright (C) 2025-2026 Bence Göblyös

# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.

# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with
# this program. If not, see https://www.gnu.org/licenses/.


"""
This module interfaces with the pico-pulse sequence synthesizer device.
"""

import sys
from pathlib import Path

if "sphinx" in sys.modules:
    PROJECT_ROOT = Path(".")
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PicoPulse:
    """
    Driver for the pico-pulse sequence synthesizer.
    """

    def __init__(
        self,
        rm,
        addr,
        pinoutName=None,
        configFile=(PROJECT_ROOT / "Config" / "PicoPulse.json"),
    ):
        """
        Parameters
        ----------
        rm : pyvisa.ResourceManager
            Pass a pyvisa ResourceManager object to use for opening the device.
        addr : str
            VISA address of the pico-pulse device.
        pinoutName : str, optional
            Name of the config file entry for the device's pin layout.
        configFile: Path, default: Config/PicoPulse.json
        """

        # Set up logger
        self.logger = logging.getLogger("instrumpy.PicoPulse")
        self.logger.propagate = True
        self.logger.setLevel(logging.NOTSET)
        self.logger.debug("Logger initialized.")

        # Try to read in pin assignments
        self.assignments = None

        if pinoutName is not None:
            conf = None
            try:
                with open(configFile, "r") as file:
                    conf = json.load(file)

            except Exception:
                self.logger.warning(
                    "Could not open config file. Pin mapping is disabled."
                )
                conf = None

            if conf is not None:
                entry = conf.get(pinoutName, None)

                if entry is not None:
                    self.assignments = entry.get("mapping", None)
                    if self.assignments is None:
                        self.logger.warning(
                            "Config entry does not contain a mapping key. Pin mapping is disabled."
                        )

                else:
                    self.logger.warning(
                        "Config does not contain the given entry. Pin mapping is disabled."
                    )

        self.device = rm.open_resource(addr)

    def _encodeSequence(self, seq, cycle=False, innerLoop=0, outerLoop=None):
        """
        Encode a sequence for transmission.

        Parameters
        ----------
        seq : pandas.DataFrame
            Sequence to be encoded. Should have at least one column from 'ch1' to 'ch5', or the mapped pins.
        cycle : bool, default : False
            Whther the timing is given in CPU cycles rather than ns.
            True is CPU cycles, False is ns.
        innerLoop : int, default : 0
            Numer of times the sequence should be copied into the transmit buffer. Helps with short sequences.
            A value of 0 will instruct the pico-pulse device to fill the entire buffer with copies.
        outerLoop : int, default: None
            Numer of times the pico-pulse should repeat the sequence.
            A value of None will instruct it to repeat the sequence indefinitely.

        Returns
        -------
        cmd: str
            Encoded command
        """
        cmd = ""
        if cycle:
            cmd += "CPULSE"
        else:
            cmd += "PULSE"

        # Set up inner loop
        m = round(innerLoop)
        if m < 0:
            m = 0

        cmd += f" {m}"

        # Set up outer loop
        if outerLoop is not None and outerLoop >= 0 and outerLoop <= (1 << 32 - 1):
            n = round(outerLoop)
        else:
            n = 1 << 32 - 1

        cmd += f" {n} "

        if self.assignments is not None:
            seq.rename(columns=self.assignments, inplace=True)

        for i in range(len(seq)):
            t = round(seq.time[i])
            t = t if t > 0 else 0

            out = 0
            if "ch1" in seq and seq.ch1[i] > 0:
                out += 1
            if "ch2" in seq and seq.ch2[i] > 0:
                out += 2
            if "ch3" in seq and seq.ch3[i] > 0:
                out += 4
            if "ch4" in seq and seq.ch4[i] > 0:
                out += 8
            if "ch5" in seq and seq.ch5[i] > 0:
                out += 16

            cmd += f"{t},{out},"

        return cmd

    def sendSequence(self, seq, **kwargs):
        """
        Encode a sequence and transmit it to the pico-pulse.

        Parameters
        ----------
        seq : pandas.DataFrame
            Sequence to be encoded. Should have at least one column from 'ch1' to 'ch5', or the mapped pins.
        cycle : bool, default : False
            Whther the timing is given in CPU cycles rather than ns.
            True is CPU cycles, False is ns.
        innerLoop : int, default : 0
            Numer of times the sequence should be copied into the transmit buffer. Helps with short sequences.
            A value of 0 will instruct the pico-pulse device to fill the entire buffer with copies.
        outerLoop : int, default: None
            Numer of times the pico-pulse should repeat the sequence.
            A value of None will instruct it to repeat the sequence indefinitely.
        """
        cmd = self._encodeSequence(seq, **kwargs)
        res = self.device.query(cmd)
        return res

    def setCurrentLimit(self, target: float):
        """
        Set the laser diode current limit.

        Parameters
        ----------
        target : float
            Current limit in amperes

        Returns
        -------
        achieved : float
            Current limit achived in amperes
        """
        resp = self.device.query(f"LIM {target}")
        return float(resp)

    def getCurrentLimit(self):
        """
        Get the laser diode current limit.

        Returns
        -------
        limit : float
            Current limit in amperes
        """
        resp = self.device.query("LIM?")
        return float(resp)

    #: float: Get or set the laser diode current limit in amperes
    currentLimit = property(fget=getCurrentLimit, fset=setCurrentLimit)

    def setMonitorTarget(self, target: float):
        """
        Set the monitor diode target current.

        Parameters
        ----------
        target : float
            Monitor current target in amperes

        Returns
        -------
        achieved : float
            Monitor diode current achived in amperes
        """
        resp = self.device.query(f"MON {target}")
        return float(resp)

    def getMonitorTarget(self):
        """
        Set the monitor diode target current.

        Returns
        -------
        limit : float
            Monitor diode current achived in amperes
        """
        resp = self.device.query("MON?")
        return float(resp)

    #: float: Get or set the monitor diode target current in amperes
    monitorTarget = property(fget=getMonitorTarget, fset=setMonitorTarget)

    def setLaser(self, target: bool):
        """
        Enables or disables the laser driver.

        Parameters
        ----------
        target : bool
            Whether the laser driver should be enabled

        Returns
        -------
        success : bool
            Indicate success
        """
        resp = self.device.query(f"LASER {'1' if target else '0'}")

        if resp.strip() != "ACK":
            # TODO: Add proper error logging or raise an exception instead
            return false

        feedback = self.device.query("LASER?")

        if int(feedback) == target:
            return True
        else:
            return False

    def getLaser(self):
        """
        Gets whether or not the laser driver is enabled.

        Returns
        -------
        state : bool
            Whether the laser driver is enabled
        """
        resp = self.device.query("LASER?")
        return bool(int(resp))

    #: bool: Get or set the state of the laser driver
    laser = property(fget=getLaser, fset=setLaser)

    def getLaserError(self):
        """
        Gets whether or not the laser driver is in an error state.

        Returns
        -------
        state : bool
            Whether the laser driver is in an error state (true is error)
        """
        resp = self.device.query("LERR?")
        return bool(int(resp))

    #: bool: Get the laser driver's error state
    laserError = property(fget=getLaserError)
