"""
GPU Device Manager - Intelligent GPU allocation with multi-GPU support and CPU fallback
"""
import torch
import threading
from collections import defaultdict
from typing import Optional

class GPUManager:
    """
    Manages GPU allocation across multiple concurrent tasks.
    Features:
    - Automatic detection of available GPUs
    - Load balancing across multiple GPUs (e.g., Tesla K80 with 2 GPUs)
    - CPU fallback when no GPU available
    - Thread-safe device assignment
    - Memory tracking per GPU
    """
    
    def __init__(self):
        self.lock = threading.Lock()
        self.gpu_usage = defaultdict(int)  # Track concurrent tasks per GPU
        self.available_gpus = self._detect_gpus()
        self.cpu_fallback = len(self.available_gpus) == 0
        
        if self.cpu_fallback:
            print("[GPUManager] No CUDA GPUs detected. Using CPU.")
        else:
            print(f"[GPUManager] Detected {len(self.available_gpus)} CUDA GPU(s): {self.available_gpus}")
            self._print_gpu_info()
    
    def _detect_gpus(self):
        """Detect all available CUDA GPUs"""
        if not torch.cuda.is_available():
            return []
        
        gpu_count = torch.cuda.device_count()
        gpus = []
        
        for i in range(gpu_count):
            try:
                # Get GPU properties
                props = torch.cuda.get_device_properties(i)
                # Only include CUDA-capable devices
                gpus.append({
                    'id': i,
                    'name': props.name,
                    'memory': props.total_memory,
                    'capability': f"{props.major}.{props.minor}"
                })
            except Exception as e:
                print(f"[GPUManager] Warning: Could not access GPU {i}: {e}")
        
        return gpus
    
    def _print_gpu_info(self):
        """Print detailed GPU information"""
        for gpu in self.available_gpus:
            memory_gb = gpu['memory'] / (1024**3)
            print(f"  GPU {gpu['id']}: {gpu['name']} "
                  f"({memory_gb:.1f}GB, Compute {gpu['capability']})")
    
    def get_device(self, task_id: Optional[int] = None) -> str:
        """
        Get the best available device for a new task.
        
        Args:
            task_id: Optional task identifier for deterministic assignment
        
        Returns:
            Device string: "cuda:0", "cuda:1", or "cpu"
        """
        with self.lock:
            if self.cpu_fallback:
                return "cpu"
            
            if len(self.available_gpus) == 0:
                return "cpu"
            
            # If task_id provided, use round-robin for deterministic assignment
            if task_id is not None:
                gpu_idx = task_id % len(self.available_gpus)
                device_id = self.available_gpus[gpu_idx]['id']
            else:
                # Load balancing: pick GPU with least current usage
                device_id = min(self.available_gpus, 
                              key=lambda g: self.gpu_usage[g['id']])['id']
            
            self.gpu_usage[device_id] += 1
            return f"cuda:{device_id}"
    
    def release_device(self, device: str):
        """Release a device after task completion"""
        with self.lock:
            if device.startswith("cuda:"):
                try:
                    device_id = int(device.split(":")[1])
                    if self.gpu_usage[device_id] > 0:
                        self.gpu_usage[device_id] -= 1
                except (ValueError, IndexError):
                    pass
    
    def get_torch_device(self, task_id: Optional[int] = None) -> torch.device:
        """
        Get a torch.device object for the best available device.
        
        Args:
            task_id: Optional task identifier for deterministic assignment
        
        Returns:
            torch.device object
        """
        device_str = self.get_device(task_id)
        return torch.device(device_str)
    
    def clear_cache(self, device: Optional[str] = None):
        """Clear CUDA cache for specified device or all devices"""
        if not torch.cuda.is_available():
            return
        
        if device and device.startswith("cuda:"):
            try:
                device_id = int(device.split(":")[1])
                with torch.cuda.device(device_id):
                    torch.cuda.empty_cache()
                print(f"[GPUManager] Cleared cache for {device}")
            except (ValueError, IndexError, RuntimeError) as e:
                print(f"[GPUManager] Warning: Could not clear cache for {device}: {e}")
        else:
            # Clear all GPUs
            for gpu in self.available_gpus:
                try:
                    with torch.cuda.device(gpu['id']):
                        torch.cuda.empty_cache()
                except RuntimeError as e:
                    print(f"[GPUManager] Warning: Could not clear cache for GPU {gpu['id']}: {e}")
            print(f"[GPUManager] Cleared cache for all GPUs")
    
    def get_memory_info(self, device_id: int = 0) -> dict:
        """Get memory usage information for a specific GPU"""
        if not torch.cuda.is_available() or device_id >= len(self.available_gpus):
            return {'allocated': 0, 'reserved': 0, 'free': 0, 'total': 0}
        
        try:
            allocated = torch.cuda.memory_allocated(device_id)
            reserved = torch.cuda.memory_reserved(device_id)
            total = self.available_gpus[device_id]['memory']
            free = total - allocated
            
            return {
                'allocated': allocated / (1024**3),  # GB
                'reserved': reserved / (1024**3),    # GB
                'free': free / (1024**3),            # GB
                'total': total / (1024**3)           # GB
            }
        except Exception as e:
            print(f"[GPUManager] Could not get memory info for GPU {device_id}: {e}")
            return {'allocated': 0, 'reserved': 0, 'free': 0, 'total': 0}
    
    def print_status(self):
        """Print current GPU usage status"""
        print("\n[GPUManager] Current Status:")
        if self.cpu_fallback:
            print("  Mode: CPU (No CUDA GPUs available)")
            return
        
        print(f"  Mode: GPU ({len(self.available_gpus)} device(s))")
        for gpu in self.available_gpus:
            gpu_id = gpu['id']
            usage = self.gpu_usage[gpu_id]
            mem = self.get_memory_info(gpu_id)
            print(f"  GPU {gpu_id} ({gpu['name']}): {usage} active tasks, "
                  f"{mem['allocated']:.1f}GB/{mem['total']:.1f}GB used")


# Global singleton instance
_gpu_manager = None

def get_gpu_manager() -> GPUManager:
    """Get the global GPU manager instance"""
    global _gpu_manager
    if _gpu_manager is None:
        _gpu_manager = GPUManager()
    return _gpu_manager


# Convenience functions
def get_device(task_id: Optional[int] = None) -> str:
    """Get device string for a task"""
    return get_gpu_manager().get_device(task_id)


def get_torch_device(task_id: Optional[int] = None) -> torch.device:
    """Get torch.device for a task"""
    return get_gpu_manager().get_torch_device(task_id)


def release_device(device: str):
    """Release a device after task completion"""
    get_gpu_manager().release_device(device)


def clear_gpu_cache(device: Optional[str] = None):
    """Clear GPU cache"""
    get_gpu_manager().clear_cache(device)


def print_gpu_status():
    """Print GPU status"""
    get_gpu_manager().print_status()
