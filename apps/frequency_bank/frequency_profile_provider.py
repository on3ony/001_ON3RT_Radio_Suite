"""
ON3RT Radio Suite
Module Banque de fréquences
Source des profils de fréquences.
"""

from apps.frequency_bank.frequency_profile import FrequencyProfile


class FrequencyProfileProvider:
    """
    Interface commune à toute source de profils de fréquences. Une
    future JSONFrequencyProfileProvider ou SQLiteFrequencyProfileProvider
    implémentera load()/save() sans qu'aucune autre partie de
    l'architecture des profils n'ait à changer.
    """

    def load(self) -> list[FrequencyProfile]:
        raise NotImplementedError

    def save(self, profiles: list[FrequencyProfile]) -> None:
        raise NotImplementedError


class DefaultFrequencyProfileProvider(FrequencyProfileProvider):
    """
    Fournit uniquement le profil par défaut, représentant exactement
    la Banque de fréquences actuelle (une seule banque, base et
    catégories inchangées) — garantit une compatibilité totale tant
    qu'aucune gestion multi-profils réelle n'est branchée. Marqué
    is_system=True : c'est le profil système de référence, protégé
    contre la suppression, comme les catégories système
    (CategoryNode.is_system). Les futurs profils créés par
    l'utilisateur resteront entièrement modifiables (is_system=False).
    """

    def load(self) -> list[FrequencyProfile]:
        return [
            FrequencyProfile(
                "Par défaut",
                description="Banque de fréquences actuelle",
                is_default=True,
                is_system=True,
            ),
        ]

    def save(self, profiles: list[FrequencyProfile]) -> None:
        pass
