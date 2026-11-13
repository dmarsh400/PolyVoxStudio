import importlib.metadata
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf
from faster_whisper.audio import decode_audio
from packaging.requirements import Requirement
from packaging.version import Version


class ReferenceAudioDependencyTests(unittest.TestCase):
    def test_pyav_constraint_excludes_incompatible_release(self):
        requirements = Path("requirements_min.txt").read_text(encoding="utf-8").splitlines()
        requirement = next(Requirement(line.split("#")[0].strip()) for line in requirements
                           if line.startswith("av>"))
        self.assertIn(Version(importlib.metadata.version("av")), requirement.specifier)
        self.assertNotIn(Version("19.0.0"), requirement.specifier)

    def test_faster_whisper_decodes_reference_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reference.wav"
            sf.write(path, np.zeros(8000, dtype=np.float32), 8000)
            decoded = decode_audio(str(path), sampling_rate=16000)
        self.assertEqual(decoded.dtype, np.float32)
        self.assertEqual(len(decoded), 16000)


if __name__ == "__main__":
    unittest.main()
