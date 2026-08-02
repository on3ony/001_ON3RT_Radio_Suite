"""
ON3RT Radio Suite
libraries/cw

Chantier CW : texte -> code Morse -> timing -> keying matériel, avec
backends interchangeables (PTT aujourd'hui, Winkeyer plus tard),
totalement indépendant de l'architecture Voix (libraries/voice/) bien
que les deux partagent les mêmes ressources CAT/PTT partagées de la
Suite (apps/cat_server/).

Architecture figée après révision (essais matériels IC-7300 + découverte
de la commande CI-V 0x17) : voir ARCHITECTURE.md dans ce même dossier
pour le schéma complet et à jour des responsabilités (CWService ->
CWDriver -> ElementDriver/TextDriver -> KeyerBackend/TextBackend).
CWService (étape 5, pas encore faite) ne connaîtra plus jamais
MorseEncoder/TimingEngine/un backend direct -- uniquement un CWDriver
injecté, choisi une seule fois dans core/application.py.
"""

from .cw_service import CWService, CWState
from .element_driver import ElementDriver
from .keyer_backend import NullKeyerBackend, NullTextKeyerBackend
from .morse_encoder import MorseElement, MorseElementKind, MorseEncoder
from .timing import TimedElement, TimingEngine

__all__ = [
    "CWService",
    "CWState",
    "ElementDriver",
    "MorseElement",
    "MorseElementKind",
    "MorseEncoder",
    "NullKeyerBackend",
    "NullTextKeyerBackend",
    "TimedElement",
    "TimingEngine",
]
