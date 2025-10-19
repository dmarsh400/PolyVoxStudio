from typing import List, Dict, Any, Optional

class TTSEngine:
    name = "Base"
    def list_voices(self) -> List[Dict[str, Any]]:
        return []
    def synthesize(self, text: str, voice_id: str, out_path: str, settings: Optional[Dict[str,Any]]=None) -> str:
        raise NotImplementedError
    def supports_cloning(self) -> bool:
        return False
    def clone_voice(self, samples: list[str], out_id: str) -> Dict[str, Any]:
        raise NotImplementedError