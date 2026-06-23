"""Vendored OG-PHL calibration constants — in-repo replacement for the ``calibration_values``
module this package used to import via a ``sys.path`` hack into CLEWS-OG/OG_simulations.

``PROD_DICT`` maps the M=4 OG-PHL production sectors to their underlying SAM activity codes
(used by ``ogphl.input_output.get_io_matrix`` to build the I-O matrix). ``CONS_DICT`` maps the I=5
consumption goods to SAM commodity codes. Both verbatim from CLEWS-OG/OG_simulations/calibration_values.py
(``CONS_DICT`` mirrors ``ogphl.constants.CONS_DICT``). Vendoring CONS_DICT lets contract.Concordance
DISCOVER the energy ports (industry+good index) from these dicts in the link env WITHOUT importing ogphl.
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

# I=5 consumption goods -> SAM commodity codes. "Energy and water" (index 1, holding celec) is the
# energy good households react to -> contract.Concordance discovers energy_good_index=1 from this.
CONS_DICT = {
    "Food": ["cmaiz", "crice", "cocer", "coils", "croot", "cvege", "csugr", "ctoba", "ccott", "cfrui",
             "ccoff", "cocrp", "ccatt", "cpoul", "coliv", "cfore", "cfish", "cfood", "cbeve"],
    "Energy and water": ["cmine", "celec", "cwatr"],
    "Non-durables": ["ctext", "cwood", "cchem", "cnmet", "cmetl"],
    "Durables": ["cmach", "coman", "ccons"],
    "Services": ["ctrad", "ctran", "chotl", "ccomm", "cfsrv", "creal", "cbsrv", "cpadm", "ceduc",
                 "cheal", "cosrv"],
}
