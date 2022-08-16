#!/usr/bin/env python3
# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import unittest

from torch import nn

from torchtnt.runner.utils import _reset_module_training_mode, _set_module_training_mode


class UtilsTest(unittest.TestCase):
    def test_set_module_training_mode(self) -> None:
        """
        Test _set_module_training_mode
        """
        module = nn.Linear(1, 1)
        loss_fn = nn.CrossEntropyLoss()

        tracked_modules = {"module": module, "loss_fn": loss_fn}

        # set module training mode to False
        prior_module_train_states = _set_module_training_mode(tracked_modules, False)

        self.assertFalse(module.training)
        self.assertFalse(loss_fn.training)

        self.assertTrue(prior_module_train_states["module"])
        self.assertTrue(prior_module_train_states["loss_fn"])

        # set back to True
        prior_module_train_states = _set_module_training_mode(tracked_modules, True)

        self.assertTrue(module.training)
        self.assertTrue(loss_fn.training)

        self.assertFalse(prior_module_train_states["module"])
        self.assertFalse(prior_module_train_states["loss_fn"])

    def test_reset_module_training_mode(self) -> None:
        """
        Test _reset_module_training_mode
        """
        module = nn.Linear(1, 1)
        loss_fn = nn.CrossEntropyLoss()

        tracked_modules = {"module": module, "loss_fn": loss_fn}

        # set module training mode to False
        prior_module_train_states = _set_module_training_mode(tracked_modules, False)

        self.assertFalse(module.training)
        self.assertFalse(loss_fn.training)

        # set back to True using reset
        _reset_module_training_mode(tracked_modules, prior_module_train_states)

        self.assertTrue(module.training)
        self.assertTrue(loss_fn.training)
