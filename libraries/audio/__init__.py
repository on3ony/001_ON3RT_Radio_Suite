"""
ON3RT Radio Suite
libraries/audio

Service audio partagé de la suite (AudioOutputService) : périphérique
de sortie sélectionné et lecture de fichiers WAV. Première brique de
l'infrastructure Voix (voir audio_output_service.py) — destinée à
devenir le point d'entrée audio unique de toute la Suite, jamais
dupliquée module par module.
"""

from .audio_output_service import AudioOutputService

__all__ = ["AudioOutputService"]
