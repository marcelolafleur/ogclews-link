"""Vendored OG-PHL calibration constants — in-repo replacement for the ``calibration_values``
module this package used to import via a ``sys.path`` hack into CLEWS-OG/OG_simulations.

``PROD_DICT`` maps the M=4 OG-PHL production sectors to their underlying SAM activity codes
(used by ``ogphl.input_output.get_io_matrix`` to build the I-O matrix). Verbatim from
CLEWS-OG/OG_simulations/calibration_values.py.
"""
from __future__ import annotations

PROD_DICT = {
    "Natural Resources": [
        "amaiz", "arice", "aocer", "aoils", "aroot", "avege", "asugr", "atoba", "acoff",
        "afrui", "acoff", "aocrp", "acatt", "apoul", "aoliv", "afore", "afish", "amine", "awatr",
    ],
    "Electricity": ["aelec"],
    "Construction, Trade, Services": [
        "acons", "atrad", "atran", "ahotl", "acomm", "afsrv", "areal", "absrv", "apadm",
        "aeduc", "aheal", "aosrv",
    ],
    "Manufacturing": [
        "afood", "abeve", "atext", "awood", "achem", "anmet", "ametl", "amach", "aoman",
    ],
}
