# Copyright (C) 2026 Bence Göblyös
#
# This program is free software: you can redistribute it and/or modify it under
#  terms of the GNU General Public License as published by the Free Software
# Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see https://www.gnu.org/licenses/.

"""
Module for interfacing with the Phase Matrix 25B microwave frequency counter
"""

"""
Phase Matrix 25B frequency counter
"""
class PM25B():
    def __init__(self, rm, addr):
        """
        Initializes the frequency counter.

        Parameters
        ----------
        rm: pyvisa.ResourceManager
            The VISA resource manager instance.
        address: str
            The VISA resource address for the counter.
        """
        self.device = rm.open_resource(addr)
        self.device.read_termination = '\r'
        self.device.write("PA")
        self.device.write("BR")

    def read(self):
        "Take a frequency and power reading and return them in Hz and dBm respectively"
        resp = self.device.read()
        freq, power = [float(x.strip()) for x in resp.split(',')]
        return freq, power
