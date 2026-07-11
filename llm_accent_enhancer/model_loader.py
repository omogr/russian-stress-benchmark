#!/usr/bin/env python3
"""

- Генератор: большая модель (например, Qwen3-4B)
- Оценщик: меньшая модель с LoRA (например, Qwen2.5-1.5B)

"""

import os

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:128"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["HF_METRICS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import torch
import torch.nn as nn
from typing import List, Dict, Optional, Tuple, Set, Union
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel
import logging
import sys
from datetime import datetime
import gc
from dataclasses import dataclass
from pathlib import Path

# "Qwen2.5-1.5B-Instruct-unsloth-bnb-4bit"

MODEL_NAME = Path.home() / "hu" / "emo" / "model" / "Qwen3-4B-Instruct-2507-unsloth-bnb-4bit"

logger = logging.getLogger(__name__)


class ModelLoader:
    def __init__(self, model_name=MODEL_NAME):
        # model_path = train_lora_config.MODEL_PATH
        # model_path = model_path.resolve()

        self.model_name = MODEL_NAME
        
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._peak_memory = 0.0

        self._setup_generator()

        logger.info(f"ModelLoader initialized on {self.device}")

    def _setup_generator(self):
        logger.info(f"Loading generator model & tokenizer: {self.model_name}")

        # 4-bit quantization config
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4"
        )

        self.generator_model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
            local_files_only=True
        )
        self.generator_tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True,
            local_files_only=True
        )

        self.generator_model.eval()
        if self.generator_tokenizer.pad_token is None:
            self.generator_tokenizer.pad_token = self.generator_tokenizer.eos_token

        logger.info(f"Generator loaded successfully, vocab size: {len(self.generator_tokenizer)}")

    def _cleanup_memory(self):
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            allocated = torch.cuda.memory_allocated() / 1024**3
            reserved = torch.cuda.memory_reserved() / 1024**3
            if allocated > self._peak_memory:
                self._peak_memory = allocated
            logger.debug(
                f"GPU Memory: {allocated:.2f}GB allocated, {reserved:.2f}GB reserved")


