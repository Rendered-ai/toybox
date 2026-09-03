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

import logging
from anatools.lib.node import Node

logger = logging.getLogger(__name__)


class Multiply(Node):
    """Simple multiplication node that multiplies two numbers together"""

    def exec(self):
        """Execute multiplication operation"""

        input_a = self.inputs["Input A"][0]
        input_b = self.inputs["Input B"][0]

        try:
            a = float(input_a)
            b = float(input_b)
        except (ValueError, TypeError) as e:
            logger.error(f"Multiply node received non-numeric inputs: A={input_a}, B={input_b}")
            raise ValueError(f"Multiply node requires numeric inputs, got A={input_a}, B={input_b}") from e

        result = a * b
        logger.info(f"Multiply: {a} * {b} = {result}")
        return {"Product": result}
