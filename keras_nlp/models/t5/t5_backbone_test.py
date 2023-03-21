# Copyright 2023 The KerasNLP Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Test for T5 backbone model."""

import os

import pytest
import tensorflow as tf
from absl.testing import parameterized
from tensorflow import keras

from keras_nlp.models.t5.t5_backbone import T5Backbone


class T5Test(tf.test.TestCase, parameterized.TestCase):
    def setUp(self):
        self.model = T5Backbone(
            vocabulary_size=4,
            num_layers=2,
            num_heads=2,
            hidden_dim=4,
            intermediate_dim=4,
        )
        self.batch_size = 2
        seq_length = 3
        self.input_batch = {
            "encoder_token_ids": tf.ones(
                (self.batch_size, seq_length), dtype="int32"
            ),
            "encoder_padding_mask": tf.ones(
                (self.batch_size, seq_length), dtype="int32"
            ),
            "decoder_token_ids": tf.ones(
                (self.batch_size, seq_length), dtype="int32"
            ),
            "decoder_padding_mask": tf.ones(
                (self.batch_size, seq_length), dtype="int32"
            ),
        }
        self.input_dataset = tf.data.Dataset.from_tensor_slices(
            self.input_batch
        ).batch(2)

    def test_valid_call_t5(self):
        self.model(self.input_batch)
        # Check default name passed through
        self.assertRegexpMatches(self.model.name, "t5_backbone")

    def test_variable_sequence_length_call_t5(self):
        for seq_length in (4, 5, 6):
            input_data = {
                "encoder_token_ids": tf.ones(
                    (self.batch_size, seq_length), dtype="int32"
                ),
                "encoder_padding_mask": tf.ones(
                    (self.batch_size, seq_length), dtype="int32"
                ),
                "decoder_token_ids": tf.ones(
                    (self.batch_size, seq_length), dtype="int32"
                ),
                "decoder_padding_mask": tf.ones(
                    (self.batch_size, seq_length), dtype="int32"
                ),
            }
            outputs = self.model(input_data)
            self.assertIn("encoder_sequence_output", outputs)
            self.assertIn("decoder_sequence_output", outputs)

    @parameterized.named_parameters(
        ("jit_compile_false", False), ("jit_compile_true", True)
    )
    def test_t5_compile(self, jit_compile):
        self.model.compile(jit_compile=jit_compile)
        outputs = self.model.predict(self.input_batch)
        self.assertIn("encoder_sequence_output", outputs)
        self.assertIn("decoder_sequence_output", outputs)

    @parameterized.named_parameters(
        ("jit_compile_false", False), ("jit_compile_true", True)
    )
    def test_t5_compile_batched_ds(self, jit_compile):
        self.model.compile(jit_compile=jit_compile)
        outputs = self.model.predict(self.input_dataset)
        self.assertIn("encoder_sequence_output", outputs)
        self.assertIn("decoder_sequence_output", outputs)

    @parameterized.named_parameters(
        ("tf_format", "tf", "model"),
        ("keras_format", "keras_v3", "model.keras"),
    )
    def test_saved_model(self, save_format, filename):
        outputs = self.model(self.input_batch)
        save_path = os.path.join(self.get_temp_dir(), filename)
        self.model.save(save_path, save_format=save_format)
        restored_model = keras.models.load_model(save_path)

        # Check we got the real object back.
        self.assertIsInstance(restored_model, T5Backbone)

        # Check that output matches.
        restored_outputs = restored_model(self.input_batch)
        for key in ["encoder_sequence_output", "decoder_sequence_output"]:
            self.assertAllClose(outputs[key], restored_outputs[key])


@pytest.mark.tpu
@pytest.mark.usefixtures("tpu_test_class")
class T5BackboneTPUTest(tf.test.TestCase, parameterized.TestCase):
    def setUp(self):
        with self.tpu_strategy.scope():
            self.model = T5Backbone(
                vocabulary_size=4,
                num_layers=2,
                num_heads=2,
                hidden_dim=4,
                intermediate_dim=4,
            )
        self.input_batch = {
            "token_ids": tf.ones((8, 4), dtype="int32"),
            "padding_mask": tf.ones((8, 4), dtype="int32"),
        }
        self.input_dataset = tf.data.Dataset.from_tensor_slices(
            self.input_batch
        ).batch(2)

    def test_predict(self):
        self.model.compile()
        outputs = self.model.predict(self.input_dataset)
        self.assertIn("encoder_sequence_output", outputs)
        self.assertIn("decoder_sequence_output", outputs)