import gc
import logging
import torch
import librosa
from .abc_provider import IaProvider
from .configs import HFCfg, convert_str2dtype
from transformers import AutoModelForCTC, AutoProcessor
from typing import Dict, Any, List

logger: logging.Logger = logging.getLogger(__file__)


class HFAudio2Text(IaProvider):

    def __init__(self, cfg: HFCfg) -> None:
        self.__name: str = cfg.name
        self.__params: Dict[str, Any] = cfg.__dict__
        self.__config: HFCfg = cfg
        self.__model = None
        self.__processor = None

    @property
    def name(self) -> str:
        return self.__name

    @classmethod
    def from_config(cls, name: str, data: Dict[str, Any]):
        return HFAudio2Text(HFCfg.load(data, name))

    @property
    def params(self) -> Dict[str, Any]:
        return self.__params

    def load(self) -> None:
        self.__model: AutoModelForCTC = AutoModelForCTC.from_pretrained(
            pretrained_model_name_or_path=self.__config.model,
            torch_dtype=convert_str2dtype(self.__config.compute_type),
        ).to(self.__config.device)
        logger.info(f"Load {self.name}  model")

        self.__processor: AutoProcessor = AutoProcessor.from_pretrained(
            pretrained_model_name_or_path=self.__config.model
        )
        logger.info(f"Load {self.name}  processor")

    def unload(self) -> None:
        del self.__model
        logger.info(f"Unload {self.name}  model")

        del self.__processor
        logger.info(f"Unload {self.name}  processor")

        gc.collect()

    def transcribe(self, audio_path: str) -> str:
        if self.__model is None or self.__processor is None:
            self.load()

        audio, sample_rate = librosa.load(audio_path, sr=16000)
        inputs = self.__processor(
            audio=audio,
            sampling_rate=16000,
            padding=True,
            return_tensors="pt"
        ).input_values

        inputs = inputs.to(self.__config.device)

        with torch.no_grad():
            logits = self.__model(inputs).logits

        predicted_ids: torch.Tensor = torch.argmax(logits, dim=-1)

        transcription: List[str] = self.__processor.batch_decode(predicted_ids)
        return transcription[0]
