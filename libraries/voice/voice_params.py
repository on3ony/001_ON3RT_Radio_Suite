"""
ON3RT Radio Suite
libraries/voice/voice_params.py

VoiceParams : paramètres de synthèse regroupés dans une structure
dédiée (dataclass immuable), plutôt que multipliés dans la signature
de VoiceService.synthesize() — un nouveau paramètre s'ajoute ici,
jamais dans l'API publique de VoiceService.

Ordre des champs FIXE (dataclass) : condition nécessaire au
déterminisme de la clé de cache — VoiceService sérialise ces champs
dans un ordre stable pour les hacher (voir voice_service.py).

voice_profile : identifiant libre (str), pas une voix concrète —
VoiceService le résout vers un moteur + une configuration réelle au
moment de la synthèse (voix système par défaut, voix clonée
principale/secondaire...). Ajouter un nouveau profil plus tard est une
question de configuration, jamais un changement d'API.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VoiceParams:
    language: str = "FR"
    engine: str | None = None          # None = sélection automatique
    voice_profile: str | None = None   # None = profil par défaut du moteur
    rate: int | None = None            # None = valeur par défaut du moteur
    volume: float | None = None        # None = valeur par défaut du moteur
