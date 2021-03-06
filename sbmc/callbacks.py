# encoding: utf-8
# Sample-based Monte Carlo Denoising using a Kernel-Splatting Network
# Michaël Gharbi Tzu-Mao Li Miika Aittala Jaakko Lehtinen Frédo Durand
# Siggraph 2019
#
# Copyright (c) 2019 Michaël Gharbi
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Callbacks used a train time."""
from numpy.core.numeric import Infinity
import torch as th

import time
import ttools
import os

from ttools.training import Trainer
import pyexr
import numpy as np
import skimage.io as skio

from ttools.utils import ExponentialMovingAverage
from ttools.modules.image_operators import crop_like
from ttools.callbacks import KeyedCallback

from sbmc.interfaces import SampleBasedDenoiserInterface
import sbmc.early_stopping as early_stopping

__all__ = ["DenoisingDisplayCallback", "TensorboardCallback", "SaveImageCallback"]

class TensorboardCallback(KeyedCallback):
    def __init__(self, log_keys, interface : SampleBasedDenoiserInterface, trainer : Trainer, checkpoint_dir=""):
        super(TensorboardCallback, self).__init__(keys=log_keys)
        self.log_keys = log_keys
        self.interface = interface
        self.writer = interface.writer
        self.model = interface.model
        self.trainer = trainer
        self.epoch = 0

        self.early_stopping = early_stopping.EarlyStopping(min_delta=1e-3, patience=20)
        self.lowest_val_loss = Infinity
        self.checkpoint_dir = checkpoint_dir

    def epoch_start(self ,epoch_idx):
        self.epoch = epoch_idx  

    def epoch_end(self):
        for name, weight in self.model.named_parameters():
            self.writer.add_histogram(name,weight, self.epoch)
            self.writer.add_histogram(f'{name}.grad',weight.grad, self.epoch)

        self.writer.add_scalar('Loss/train', self.ema["loss"], self.epoch)
        self.writer.add_scalar('RMSE/train', self.ema["rmse"], self.epoch)
    
    def validation_end(self, val_data):
        self.writer.add_scalar('Loss/validation', val_data['loss'], self.epoch)
        self.writer.add_scalar('RMSE/validation', val_data['rmse'], self.epoch)

        print(f"Validation loss: {val_data['loss']} rmse: {val_data['rmse']}")

        if self.early_stopping.step(th.tensor(val_data['loss'])):
            print(f"Validation loss converged at epoch {self.epoch} with loss {val_data['loss']}")
            self.trainer._stop()

        location = os.path.join(self.checkpoint_dir, "best")
        os.makedirs(location, exist_ok=True)

        if (val_data['loss'] < self.lowest_val_loss):
            self.lowest_val_loss = val_data['loss']
            # Save a copy of the model when the validation loss is at the lowest
            th.save({
                'model_state_dict': self.interface.model.state_dict(),
                'optimizer_state_dict': self.interface.optimizer.state_dict(),
                'epoch': self.epoch
            }, os.path.join(self.checkpoint_dir, "best/best.pth"))

class SaveImageCallback(ttools.Callback):
    def __init__(self, freq=50, checkpoint_dir=""):
        super(SaveImageCallback, self).__init__()
        self.epoch = 0

        self.steps = 0
        self.freq = freq
        self.checkpoint_dir = checkpoint_dir

    def batch_end(self, batch, fwd_result, bwd_result):
        if self.steps % self.freq != 0:
            self.steps += 1
            return

        self.steps = 0

        self.visualized_image(batch, fwd_result)
        self.steps += 1

    def visualized_image(self, batch, fwd_result):
        lowspp = batch["low_spp"].detach()
        target = batch["target_image"].detach()
        output = fwd_result["radiance"].detach()

        # Make sure images have the same size
        lowspp = crop_like(lowspp, output)
        target = crop_like(target, output)

        # Assemble a display gallery
        diff = (output-target).abs()
        data = th.cat([lowspp, output, target, diff], -2)

        # Clip and tonemap
        data = th.clamp(data, 0)
        data /= 1 + data
        data = th.pow(data, 1.0/2.2)
        data = th.clamp(data, 0, 1)

        data_save = data[0, ...].cpu().detach().numpy().transpose([1, 2, 0])
        
        # Save a denoising of initialised network
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        outputfile = os.path.join(self.checkpoint_dir, f'{time.time()}.png')
        pyexr.write(outputfile, data_save)
        
        png = outputfile.replace(".exr", ".png")
        skio.imsave(png, (np.clip(data_save, 0, 1)*255).astype(np.uint8))

        return data

class DenoisingDisplayCallback(ttools.ImageDisplayCallback):
    """A callback that periodically displays denoising results.

    Shows a single batch every few training steps, as well as another
    set of images during validation.

    See :class:`ttools.ImageDisplayCallback`'s documentation for more info.
    """
    def __init__(self, frequency=100, server=None, port=8097, env="main", base_url="/", win=None, checkpoint_dir=""):
        super(DenoisingDisplayCallback, self).__init__(frequency, server, port, env, base_url, win)

        self.checkpoint_dir = checkpoint_dir

    def caption(self, batch, fwd_result):
        spp = batch["spp"][0].item()
        return "vertically: %dspp, ours, target, difference" % spp

    def visualized_image(self, batch, fwd_result):
        lowspp = batch["low_spp"].detach()
        target = batch["target_image"].detach()
        output = fwd_result["radiance"].detach()

        # Make sure images have the same size
        lowspp = crop_like(lowspp, output)
        target = crop_like(target, output)

        # Assemble a display gallery
        diff = (output-target).abs()
        data = th.cat([lowspp, output, target, diff], -2)

        # Clip and tonemap
        data = th.clamp(data, 0)
        data /= 1 + data
        data = th.pow(data, 1.0/2.2)
        data = th.clamp(data, 0, 1)

        data_save = data[0, ...].cpu().detach().numpy().transpose([1, 2, 0])
        
        # Save a denoising of initialised network
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        outputfile = os.path.join(self.checkpoint_dir, f'{time.time()}.png')
        pyexr.write(outputfile, data_save)
        
        png = outputfile.replace(".exr", ".png")
        skio.imsave(png, (np.clip(data_save, 0, 1)*255).astype(np.uint8))

        return data
