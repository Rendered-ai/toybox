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


class Addition(Node):
    """Simple addition node that adds two numbers together"""

    def exec(self):
        """Execute addition operation"""

        # Get inputs - handle both direct values and linked inputs
        input_a = self.inputs["Input A"][0]
        input_b = self.inputs["Input B"][0]

        # Convert to float to handle both int and float inputs
        try:
            a = float(input_a)
            b = float(input_b)
        except (ValueError, TypeError) as e:
            logger.error(f"Addition node received non-numeric inputs: A={input_a}, B={input_b}")
            raise ValueError(f"Addition node requires numeric inputs, got A={input_a}, B={input_b}") from e

        result = a + b
        logger.info(f"Addition: {a} + {b} = {result}")
        return {"Sum": result}
