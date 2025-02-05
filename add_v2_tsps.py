# ============================================================================
#  COPYRIGHT KONINKLIJKE PHILIPS ELECTRONICS N.V. 2024
#  All rights are reserved. Reproduction in whole or in part is
#  prohibited without the written consent of the copyright owner.
# ============================================================================

import argparse
import csv
import fnmatch
import itertools
import logging
import os
import shutil
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import List


def _parse_args():
    not_testing = "--test" not in sys.argv and "-t" not in sys.argv
    parser = argparse.ArgumentParser(
        prog="Add V2 TSPs to csv files.",
        description="Updates Voyager PresetModeSpec.csv with V2 TSPs and modifies the V1 internal capabilities as necessary.",
        epilog="",
    )
    parser.add_argument(
        "--repo",
        "-r",
        dest="repo",
        required=not_testing,
        help="ULTVMQ repo to modify",
    )
    parser.add_argument(
        "--input",
        "-i",
        dest="input",
        required=not_testing,
        help="CSV file that describes which TSPs to upgrade to V2 in format: Product, Transducer, Preset",
    )
    parser.add_argument(
        "-l",
        "--log",
        dest="log_level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    parser.add_argument(
        "--test", "-t", action="store_true", help="Run script test suite."
    )
    return parser.parse_args()


class _TestAddV2Tsps(unittest.TestCase):
    def test_todo(self):
        self.assertTrue(False)


def _test():
    print("Running test suite instead of script.")
    runner = unittest.TextTestRunner()
    itersuite = unittest.TestLoader().loadTestsFromTestCase(_TestAddV2Tsps)
    runner.run(itersuite)
    exit(0)


VGR_XCDR_DATA_DIR = Path("vgrXdcrData") / "sh"
PRESET_MODE_SPEC_FILE = VGR_XCDR_DATA_DIR / "PresetModeSpec.csv"


def create_copy(file_path: Path):
    backup_path = file_path.with_suffix(file_path.suffix + ".bak")
    shutil.copy(file_path, backup_path)
    return backup_path


@dataclass
class Tsp:
    product: str
    transducer: str
    preset: str


V1_CAPABILITY = "TspV1"
V2_CAPABILITY = "TspV2"


def read_tsp_csv(file_path: Path) -> List[Tsp]:
    tsp_list = []
    with open(file_path, "r") as f:
        reader = csv.reader(f)
        _ = next(reader)
        for row in reader:
            product, transducer, preset = row
            tsp_list.append(Tsp(product=product, transducer=transducer, preset=preset))
    return tsp_list


class PresetModeSpecInfo:
    def __init__(self, preset_mode_spec_file: Path):
        self.preset_mode_spec_file = preset_mode_spec_file
        with open(preset_mode_spec_file, "r") as f:
            pms_csv_reader = csv.reader(f)
            header = next(pms_csv_reader)
        self.header = header
        self.product_index = header.index("Product")
        self.transducer_index = header.index("Transducer")
        self.preset_index = header.index("Preset")
        self.capability_id_index = header.index("Capability Id")


def update_pms(preset_mode_spec_file: Path, tsp_upgrade_list):
    temp = create_copy(preset_mode_spec_file)
    pms_info = PresetModeSpecInfo(preset_mode_spec_file)
    with open(temp, "r") as f_in:
        pms_csv_reader = csv.reader(f_in)
        reader1, reader2 = itertools.tee(pms_csv_reader)
        next(reader2)
        with open(preset_mode_spec_file, "w", newline="") as f_out:
            header = next(reader1)
            next(reader2)
            pms_csv_writer = csv.writer(f_out)
            pms_csv_writer.writerow(header)
            for row, next_row in itertools.zip_longest(reader1, reader2):
                found_match = False
                for tsp in tsp_upgrade_list:
                    if (
                        fnmatch.fnmatch(row[pms_info.product_index], tsp.product)
                        and fnmatch.fnmatch(
                            row[pms_info.transducer_index], tsp.transducer
                        )
                        and fnmatch.fnmatch(row[pms_info.preset_index], tsp.preset)
                    ):
                        if not next_row[pms_info.preset_index].endswith(" 2"):
                            found_match = True
                            row[pms_info.capability_id_index] = V1_CAPABILITY
                            pms_csv_writer.writerow(row)
                            row_v2 = row.copy()
                            row_v2[pms_info.preset_index] = (
                                row[pms_info.preset_index] + " 2"
                            )
                            row_v2[pms_info.capability_id_index] = V2_CAPABILITY
                            pms_csv_writer.writerow(row_v2)
                            print(
                                f"Adding V2 TSP for: {row_v2[pms_info.product_index]}, {row_v2[pms_info.transducer_index]}, {row_v2[pms_info.preset_index]}"
                            )
                if not found_match:
                    pms_csv_writer.writerow(row)
    os.remove(temp)


def main(args):
    preset_mode_spec_file = Path(args.repo) / PRESET_MODE_SPEC_FILE
    tsp_upgrade_list = read_tsp_csv(Path(args.input))
    update_pms(preset_mode_spec_file, tsp_upgrade_list)


if __name__ == "__main__":
    args = _parse_args()
    if args.log_level:
        logging.basicConfig(level=getattr(logging, args.log_level))
    if args.test:
        _test()

    main(args)
