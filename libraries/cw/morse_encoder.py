"""
ON3RT Radio Suite
libraries/cw/morse_encoder.py

MorseEncoder : texte -> séquence d'éléments Morse abstraits (dit/dah +
espaces), deuxième brique du chantier CW. Utilise MORSE_TABLE
(libraries/cw/morse_table.py, étape 1) pour la correspondance
caractère/code, mais n'a AUCUNE notion de durée ni de vitesse (WPM) —
cette séparation stricte avec TimingEngine (étape 3, prochaine) est la
même discipline que celle déjà en place entre VoiceService et ses
moteurs interchangeables : chaque brique ne fait qu'une seule chose.

Pipeline complet (voir docstring de libraries/cw/__init__.py) :
    Texte -> MorseEncoder -> TimingEngine -> CWService -> KeyerBackend

char_index sur chaque élément produit : index du caractère, dans le
TEXTE SOURCE (pas une position dans la séquence encodée), auquel cet
élément appartient — indispensable pour que CWService (étape 5) puisse
signaler une progression ("caractère N/total en cours d'émission") en
se référant directement au texte affiché à l'opérateur (zone de
saisie libre ou macro résolue), jamais à une position dans la séquence
encodée qui n'a aucun sens pour l'interface. Voir aussi l'architecture
validée : macros F1-F12 et saisie libre partagent le même pipeline
jusqu'ici, MorseEncoder ne les distingue jamais.

Espaces (limites de mot) : un ou plusieurs espaces consécutifs entre
deux mots produisent un seul GAP_WORD (jamais un GAP_WORD par espace).
Des espaces en début ou fin de texte ne produisent jamais un gap
"orphelin" : la séquence produite commence et finit toujours par un
DIT/DAH, jamais par un élément d'espacement.

Caractères non pris en charge par MORSE_TABLE (accents, symboles non
couverts) : ignorés silencieusement, jamais d'exception — même
philosophie que radio_phonetics.py. Un caractère ignoré au milieu d'un
mot ne casse pas l'espacement du reste : les lettres valides autour de
lui restent séparées par un espace inter-lettre normal, comme s'il
n'avait jamais existé dans le texte.

Signes procéduraux (prosignes UIT : BT, AR, SK, KN...) : toujours pas
pris en charge à cette étape (voir morse_table.py). Un prosigne
s'encoderait comme un groupe de lettres SANS le GAP_LETTER qui les
sépare habituellement — ce sera une extension explicite de encode(),
le moment venu, pas un changement de MORSE_TABLE.

Signalement des caractères ignorés (texte normalisé, caractères
ignorés, position) : PAS implémenté à cette étape, mais compatible
sans casser encode() — une future méthode additionnelle (ex.
unsupported_characters(text) -> list[tuple[int, str]], ou un
encode_report(text) plus complet) pourra être ajoutée à côté de
encode() sans jamais modifier sa signature ni son comportement actuel,
exactement comme synthesize_to_buffer() a été anticipé pour
VoiceService sans jamais être ajouté prématurément.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from libraries.cw.morse_table import MORSE_TABLE


class MorseElementKind(Enum):
    """Type d'un élément Morse abstrait — aucune durée associée, voir TimingEngine (étape suivante)."""

    DIT = "dit"
    DAH = "dah"
    GAP_SYMBOL = "gap_symbol"  # entre deux points/traits d'une même lettre (1 unité, côté TimingEngine)
    GAP_LETTER = "gap_letter"  # entre deux lettres d'un même mot (3 unités, côté TimingEngine)
    GAP_WORD = "gap_word"      # entre deux mots (7 unités, côté TimingEngine)


@dataclass(frozen=True, slots=True)
class MorseElement:
    """Un élément Morse abstrait, avec son caractère d'origine — voir docstring du module (char_index)."""

    kind: MorseElementKind
    char_index: int


class MorseEncoder:
    """Encode un texte en séquence de MorseElement — voir docstring du module pour l'ensemble des garanties."""

    def encode(self, text: str) -> list[MorseElement]:
        elements: list[MorseElement] = []
        pending_word_gap = False
        first_char_emitted = False

        for index, char in enumerate(text):
            if char == " ":
                if first_char_emitted:
                    pending_word_gap = True
                continue

            code = MORSE_TABLE.get(char.upper())
            if code is None:
                continue

            if first_char_emitted:
                gap_kind = MorseElementKind.GAP_WORD if pending_word_gap else MorseElementKind.GAP_LETTER
                elements.append(MorseElement(kind=gap_kind, char_index=index))

            pending_word_gap = False

            for symbol_index, symbol in enumerate(code):
                if symbol_index > 0:
                    elements.append(MorseElement(kind=MorseElementKind.GAP_SYMBOL, char_index=index))
                symbol_kind = MorseElementKind.DIT if symbol == "." else MorseElementKind.DAH
                elements.append(MorseElement(kind=symbol_kind, char_index=index))

            first_char_emitted = True

        return elements
