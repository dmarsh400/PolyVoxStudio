"""
Wrapper to run the EnglishBookNLP pipeline.
"""

import logging
from pathlib import Path
import torch

from app.core.english_booknlp import EnglishBookNLP

logger = logging.getLogger(__name__)


def run_booknlp(input_path, output_dir, prefix, model, pipeline):
    """
    Run BookNLP processing with GPU management.
    """
    import torch
    from app.core.gpu_manager import get_device, release_device
    
    # Get device for this task
    device_str = get_device()
    
    # Convert to torch.device
    device = torch.device(device_str) if device_str else None
    
    # Set the default CUDA device for this process
    if device_str.startswith("cuda:"):
        device_id = int(device_str.split(":")[1])
        torch.cuda.set_device(device_id)
        print(f"[booknlp_runner] Using device: {device_str}")
    else:
        print(f"[booknlp_runner] Using device: {device_str}")
    
    # Clear GPU cache before starting
    torch.cuda.empty_cache()
    
    try:
        # Initialize BookNLP model
        booknlp = EnglishBookNLP({"model": model, "pipeline": pipeline}, device=device)
        
        # Process the input file
        booknlp.process(input_path, output_dir, prefix)
        
        print(f"[booknlp_runner] Processing complete for {prefix}")
        
    finally:
        # Release the device back to the pool
        release_device(device_str)
