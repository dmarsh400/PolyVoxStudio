"""
Wrapper to run the EnglishBookNLP pipeline.
"""

import logging
from pathlib import Path

from app.core.english_booknlp import EnglishBookNLP

logger = logging.getLogger(__name__)


def run_booknlp(input_path: str, output_dir: str, overwrite: bool = True, prefix: str = None, model: str = "big", pipeline: str = "entity,quote,coref"):
    """
    Run the EnglishBookNLP pipeline on the given text file.

    Args:
        input_path: Path to the input .txt file
        output_dir: Path to the output directory
        overwrite: Whether to overwrite existing files
        prefix: Optional prefix for output files (defaults to input filename stem)
        model: Model size ("small" or "big")
        pipeline: Pipeline string

    Returns:
        Path to the output directory (str)
    """
    model_params = {
        "model": model,
        "spacy_model": "en_core_web_md",
        "pipeline": pipeline,
    }

    booknlp = EnglishBookNLP(model_params)

    if prefix is None:
        prefix = Path(input_path).stem  # fallback to input name

    logger.info(
        f"[BookNLP Runner] Processing {input_path} → {output_dir}, prefix={prefix}, model={model}, pipeline={pipeline}"
    )

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    booknlp.process(input_path, output_dir, prefix)

    return str(output_dir)
