"""
ON3RT Radio Suite
Module Banque de fréquences
Gestion du profil actif.

Point d'entrée unique pour "quel profil est actif" et "quelles
catégories lui appartiennent". Aujourd'hui, un seul profil système
("Par défaut") existe : le comportement observable reste strictement
identique à une utilisation directe de
CategoryStore(DefaultCategoryProvider()). Lorsqu'un second profil sera
introduit, ni CategoryStore ni l'interface n'auront besoin d'être
modifiés — seule la source de catégories associée au nouveau profil
change (voir CategoryProvider).
"""

from apps.frequency_bank.category_provider import DefaultCategoryProvider
from apps.frequency_bank.category_store import CategoryStore
from apps.frequency_bank.frequency_profile import FrequencyProfile
from apps.frequency_bank.frequency_profile_provider import FrequencyProfileProvider


class FrequencyProfileManager:

    def __init__(self, provider: FrequencyProfileProvider):
        self._provider = provider
        self.profiles: list[FrequencyProfile] = provider.load()

        if not self.profiles:
            raise ValueError("Aucun profil fourni par le FrequencyProfileProvider")

        # Un CategoryStore indépendant par profil — aujourd'hui tous
        # construits depuis le même DefaultCategoryProvider (aucune
        # vraie séparation de données), mais l'architecture est prête
        # à recevoir un provider distinct par profil sans changer une
        # seule ligne de cette classe.
        self._category_stores: dict[str, CategoryStore] = {
            profile.id: CategoryStore(DefaultCategoryProvider())
            for profile in self.profiles
        }

        default_profile = next((p for p in self.profiles if p.is_default), self.profiles[0])
        self.active_profile_id: str = default_profile.id

    @property
    def active_profile(self) -> FrequencyProfile:
        return next(p for p in self.profiles if p.id == self.active_profile_id)

    @property
    def active_category_store(self) -> CategoryStore:
        return self._category_stores[self.active_profile_id]

    def set_active_profile(self, profile_id: str) -> None:
        if profile_id not in self._category_stores:
            raise ValueError(f"Profil introuvable : {profile_id}")

        self.active_profile_id = profile_id

    def find_profile(self, profile_id: str) -> FrequencyProfile | None:
        return next((p for p in self.profiles if p.id == profile_id), None)
