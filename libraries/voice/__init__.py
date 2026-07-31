"""
ON3RT Radio Suite
libraries/voice

Service de synthèse vocale partagé de la Suite (VoiceService) : texte
-> fichier audio, avec cache et résolution des variables %CLE% — voir
voice_service.py. Quatrième brique de l'architecture Voix, totalement
indépendante de PTTGuard/TransmissionService (apps/cat_server/).
"""

from .voice_params import VoiceParams
from .voice_service import VoiceService

__all__ = ["VoiceParams", "VoiceService"]
