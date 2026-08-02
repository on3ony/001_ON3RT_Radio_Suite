"""
ON3RT Radio Suite
libraries/cw/timing.py

TimingEngine : convertit une séquence de MorseElement (dit/dah/espaces
abstraits, libraries/cw/morse_encoder.py, étape 2) en durées concrètes
(secondes), selon la vitesse en mots par minute (WPM) — et, si activé,
une vitesse Farnsworth distincte. Troisième brique du chantier CW :
aucune dépendance à Qt, au matériel, ni à un quelconque backend de
keying — pur calcul, comme MorseEncoder et morse_table.py avant lui.

Pipeline complet (voir docstring de libraries/cw/__init__.py) :
    Texte -> MorseEncoder -> TimingEngine -> CWService -> KeyerBackend

Référence de vitesse : la définition internationale du "mot par
minute" (WPM) en télégraphie repose sur le mot "PARIS" — envoyer
"PARIS " en boucle pendant une minute à N WPM prend exactement une
minute. "PARIS " (avec l'espace de mot qui suit) totalise 50 unités de
durée : vérifié empiriquement avec le vrai MorseEncoder (P+A+R+I+S =
31 unités de contenu — dits/dahs/espaces intra-caractère — et 12
unités d'espaces inter-caractère internes + 7 unités d'espace de mot
final = 19 unités d'espacement ; 31+19 = 50). Une unité (un "dit")
dure donc 1.2/WPM secondes.

Durées standard (sans Farnsworth) :
    DIT          = 1 unité
    DAH          = 3 unités
    GAP_SYMBOL   = 1 unité (intra-caractère)
    GAP_LETTER   = 3 unités (inter-caractère)
    GAP_WORD     = 7 unités (inter-mot)

Farnsworth (farnsworth_wpm optionnel, toujours <= wpm) : garde les
dits/dahs et les espaces intra-caractère à la vitesse "caractère"
(wpm) — pour que chaque lettre garde sa forme/son reconnaissable à
vitesse normale — mais ALLONGE les espaces inter-caractère et
inter-mot pour ramener la vitesse GLOBALE du message à
farnsworth_wpm. Formule standard, dérivée du mot de référence "PARIS"
(31 unités de contenu, 19 unités d'espacement) :

    ta = 1.2 / wpm                          (unité "caractère")
    tb = (60/farnsworth_wpm - 31*ta) / 19    (unité "espacement", Farnsworth)

Si farnsworth_wpm vaut None (ou == wpm), tb == ta exactement (continu
à la frontière, vérifié par calcul) : comportement standard, sans
Farnsworth. farnsworth_wpm > wpm n'a pas de sens (le Farnsworth
ralentit un message, jamais l'inverse) : levé comme ValueError, jamais
silencieusement corrigé ou inversé — un réglage incohérent doit être
signalé clairement, pas deviné. Cette contrainte (farnsworth_wpm <=
wpm) garantit aussi mathématiquement que tb >= ta dans tous les cas
valides : tb ne peut jamais devenir plus court que ta ni négatif.
"""

from __future__ import annotations

from dataclasses import dataclass

from libraries.cw.morse_encoder import MorseElement, MorseElementKind

_PARIS_CONTENT_UNITS = 31  # dits/dahs/espaces intra-caracteres du mot de reference "PARIS"
_PARIS_SPACING_UNITS = 19  # espaces inter-caracteres + espace de mot du mot de reference "PARIS"

_UNITS_BY_KIND: dict[MorseElementKind, int] = {
    MorseElementKind.DIT: 1,
    MorseElementKind.DAH: 3,
    MorseElementKind.GAP_SYMBOL: 1,
    MorseElementKind.GAP_LETTER: 3,
    MorseElementKind.GAP_WORD: 7,
}

# A vitesse "caractere" (ta) : dits/dahs et espaces intra-caractere,
# pour garder la forme/le son de chaque lettre reconnaissable meme en
# Farnsworth. Le reste (GAP_LETTER/GAP_WORD) est a vitesse
# "espacement" (tb) -- voir docstring du module.
_CHARACTER_SPEED_KINDS = frozenset(
    {MorseElementKind.DIT, MorseElementKind.DAH, MorseElementKind.GAP_SYMBOL}
)


@dataclass(frozen=True, slots=True)
class TimedElement:
    """Un MorseElement associé à sa durée réelle en secondes — voir docstring du module."""

    kind: MorseElementKind
    char_index: int
    duration_s: float


class TimingEngine:
    """Convertit des MorseElement en TimedElement selon le WPM (et Farnsworth optionnel) — voir docstring du module."""

    def __init__(self, wpm: float, farnsworth_wpm: float | None = None):
        if wpm <= 0:
            raise ValueError(f"wpm doit être strictement positif (reçu : {wpm}).")

        if farnsworth_wpm is not None:
            if farnsworth_wpm <= 0:
                raise ValueError(f"farnsworth_wpm doit être strictement positif (reçu : {farnsworth_wpm}).")
            if farnsworth_wpm > wpm:
                raise ValueError(
                    f"farnsworth_wpm ({farnsworth_wpm}) ne peut pas dépasser wpm ({wpm}) — "
                    "le Farnsworth ralentit un message, jamais l'inverse."
                )

        self.wpm = wpm
        self.farnsworth_wpm = farnsworth_wpm

        self._character_unit_s = 1.2 / wpm
        self._spacing_unit_s = self._compute_spacing_unit_s()

    def _compute_spacing_unit_s(self) -> float:
        if self.farnsworth_wpm is None or self.farnsworth_wpm >= self.wpm:
            return self._character_unit_s

        total_word_time_s = 60.0 / self.farnsworth_wpm
        content_time_s = _PARIS_CONTENT_UNITS * self._character_unit_s
        return (total_word_time_s - content_time_s) / _PARIS_SPACING_UNITS

    def apply(self, elements: list[MorseElement]) -> list[TimedElement]:
        """Traduit chaque MorseElement en TimedElement — jamais de mutation des éléments d'entrée."""

        timed: list[TimedElement] = []

        for element in elements:
            unit_s = self._character_unit_s if element.kind in _CHARACTER_SPEED_KINDS else self._spacing_unit_s
            duration_s = _UNITS_BY_KIND[element.kind] * unit_s
            timed.append(TimedElement(kind=element.kind, char_index=element.char_index, duration_s=duration_s))

        return timed
