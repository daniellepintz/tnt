# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

import logging
from typing import Iterable, Optional

import torch

from torchtnt.runner.progress import Progress
from torchtnt.runner.state import EntryPoint, PhaseState, State
from torchtnt.runner.unit import EvalUnit, TEvalData
from torchtnt.runner.utils import (
    _check_loop_condition,
    _is_epoch_done,
    _reset_module_training_mode,
    _set_module_training_mode,
)

logger: logging.Logger = logging.getLogger(__name__)


def evaluate(
    eval_unit: EvalUnit,
    dataloader: Iterable[TEvalData],
    *,
    max_steps_per_epoch: Optional[int] = None,
) -> State:
    """Makes a single pass through the evaluation dataloader."""
    state = State(
        entry_point=EntryPoint.EVALUATE,
        eval_state=PhaseState(
            dataloader=dataloader,
            max_steps_per_epoch=max_steps_per_epoch,
            progress=Progress(),
        ),
    )
    try:
        _check_loop_condition("max_steps_per_epoch", max_steps_per_epoch)
        logger.info(
            f"Started evaluation with max_steps_per_epoch={max_steps_per_epoch}"
        )
        _evaluate_impl(state, eval_unit)
        logger.info("Finished evaluation")
        return state
    except Exception as e:
        # TODO: log for diagnostics
        logger.info(e)
        eval_unit.on_exception(state, e)
        raise e


@torch.inference_mode()
def _evaluate_impl(
    state: State,
    eval_unit: EvalUnit,
) -> None:
    # Set all modules to eval mode
    # access modules made available through _AppStateMixin
    tracked_modules = eval_unit.tracked_modules()
    prior_module_train_states = _set_module_training_mode(tracked_modules, False)

    eval_unit.on_eval_start(state)

    eval_state = state.eval_state
    assert eval_state is not None

    # Conditionally run this to avoid running this multiple times
    # in the case of resuming from a checkpoint mid-epoch
    if eval_state.progress.num_steps_completed_in_epoch == 0:
        eval_unit.on_eval_epoch_start(state)

    data_iter = iter(eval_state.dataloader)

    while not _is_epoch_done(eval_state.progress, eval_state.max_steps_per_epoch):
        try:
            # TODO: conditionally expose data iterator for use cases that require access during the step
            batch = next(data_iter)
            eval_state.step_output = eval_unit.eval_step(state, batch)
            # clear step_output to avoid retaining extra memory
            eval_state.step_output = None
            eval_state.progress.num_steps_completed_in_epoch += 1
            eval_state.progress.num_steps_completed += 1
        except StopIteration:
            break
    eval_unit.on_eval_epoch_end(state)

    # set progress counters for the next epoch
    eval_state.progress.num_epochs_completed += 1
    eval_state.progress.num_steps_completed_in_epoch = 0

    eval_unit.on_eval_end(state)

    # Reset training mode for modules at the end of the epoch
    # This ensures that side-effects made by the loop are reset before
    # returning back to the user
    _reset_module_training_mode(tracked_modules, prior_module_train_states)
