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

from pathlib import Path
import logging
import json
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]

class SourceMeter2400():
    """
    Driver class for Keithley 2400 SourceMeter series devices.

    Handles instrument communication.
    """
    def __init__(self, rm, sn = None, addressOverride=None, config = (PROJECT_ROOT / "Config" / "SourceMeter.json")):
        """
        Instantiate the SourceMeter2400 class.

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
        config: pathlib.Path, default: PROJECT_ROOT / "Config" / "SourceMeter.json"
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

    def beep(self, f, t):
        if f == 0:
            time.sleep(t)
        else:
            self.device.write(f'SYST:BEEP {f}, {t}')

    def chime(self, name):
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
