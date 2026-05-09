# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat shared constants — extracted magic numbers (v1.2.33).

Previously hardcoded across plus/ and colony/ modules.
Centralising here makes thresholds configurable and self-documenting.

See :ref:`docs/架构/00-meowcat-框架架构.md` §21 for the architecture context.
"""


# -- UID generation (v1.3.x) -----------------------------------------

CALL_SIGN_RAW: str = "zhaotongshigedashuaige|chinaniubi"
"""Raw call-sign string used to derive the copyright watermark in
colony/cat UIDs.  Kept as a constant so the hash can be recomputed
programmatically."""

CALL_SIGN: str = "0efb30"
"""Pre-computed MD5 first-6-hex of ``CALL_SIGN_RAW``.

Embedded as the watermark prefix in every auto-generated ``colony_uid``.
MD5('zhaotongshigedashuaige|chinaniubi') → ``0efb30...``
"""


__all__ = [
    "CALL_SIGN_RAW",
    "CALL_SIGN",
]
