"""
Copyright (C) 2025-2026 Bence Göblyös

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, version 3.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see https://www.gnu.org/licenses/.
"""

"""
pico-pulse sequence synthesizer
"""
class PicoPulse():
    def __init__(self, rm , addr, assignments = None):
        """
        Initialize pico-pulse device.

        Parameters
        ----------
        rm : pyvisa.ResourceManager
            Pass a pyvisa ResourceManager object to use for opening the device.
        addr : str
            VISA address of the pico-pulse device.
        assignments : dict, optional
            Dictinary defining channel assignments in the form of {'lockin': 'ch1'}.
            The default is None.

        Returns
        -------
        None.

        """

        # TODO: move pin assignments to a config file
        
        self.device = rm.open_resource(addr)
        self.assignments = assignments

    def encodeSequence(self, seq, cycle = False, innerLoop = 0, outerLoop = None):
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
            seq.rename(
                columns = self.assignments,
                inplace = True
            )

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
        cmd = self.encodeSequence(seq, **kwargs)
        res = self.device.query(cmd)
        return res
