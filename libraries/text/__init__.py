"""
ON3RT Radio Suite
libraries/text

Utilitaires de traitement de texte partagés par toute la Suite,
indépendants de tout module applicatif (voir variable_resolver.py).
"""

from .variable_resolver import resolve_variables

__all__ = ["resolve_variables"]
