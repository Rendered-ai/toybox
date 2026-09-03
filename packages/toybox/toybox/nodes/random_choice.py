# Copyright 2019-2022 DADoES, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the root directory in the "LICENSE" file or at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging

import numpy as np

import anatools.lib.context as ctx
from anatools.lib.node import Node

logger = logging.getLogger(__name__)


class RandomChoice(Node):
    """Randomly select one option from a list of inputs.

    The Options input is expected to be a JSON-encoded list (e.g. ``["a","b","c"]``)
    or a list provided via upstream links. The selection is deterministic with respect
    to ``ctx.seed + ctx.interp_num`` so reruns of the same job are reproducible.
    """

    def exec(self):
        rng = np.random.default_rng(ctx.seed + ctx.interp_num)
        raw = self.inputs["Options"][0]
        if isinstance(raw, str):
            options = json.loads(raw)
        else:
            options = list(raw)
        selection = rng.choice(options)
        # numpy scalar types are not always JSON-serializable downstream; coerce.
        try:
            selection = selection.item()
        except AttributeError:
            pass
        logger.info("RandomChoice - options=%s, selected=%s", options, selection)
        return {"Selection": selection}
