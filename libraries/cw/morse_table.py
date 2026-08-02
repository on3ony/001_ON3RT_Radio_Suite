"""
ON3RT Radio Suite
libraries/cw/morse_table.py

Table caractère -> code Morse international (UIT), première brique du
chantier CW. Utilisée par MorseEncoder (libraries/cw/morse_encoder.py,
étape suivante) pour transformer un texte en séquence d'éléments Morse
abstraits — cette table ne fait QUE l'association caractère/code,
aucune notion de durée, de vitesse (WPM) ni de matériel : cette
séparation stricte est la même que celle déjà en place entre
MorseEncoder/TimingEngine/CWService/KeyerBackend (voir docstring du
chantier CW).

Représentation : chaque caractère est associé à une chaîne composée
uniquement de points (".") et de traits ("-") — la notation universelle
du code Morse. Aucune unité de temps ici (voir TimingEngine, étape 3,
pour la conversion en secondes selon le WPM/Farnsworth) : un trait est
toujours "trois fois plus long qu'un point", jamais un nombre concret
de millisecondes à ce niveau.

Clés toujours en MAJUSCULES : MORSE_TABLE ne connaît pas la casse —
c'est à l'appelant (MorseEncoder, étape suivante) de normaliser le
texte avant consultation, exactement comme radio_phonetics.py le fait
déjà pour l'alphabet radio international (même discipline, même
raison : une seule source de vérité pour la normalisation, jamais
dupliquée dans chaque table).

Portée couverte : les 26 lettres, les 10 chiffres, et la ponctuation
standard du code Morse international la plus documentée. Un caractère
absent de cette table (accent, symbole non couvert...) n'a PAS de
comportement défini ici — c'est une décision de MorseEncoder (étape
suivante), pas de cette table, qui reste une donnée pure sans logique.

Signes procéduraux (prosignes UIT : BT, AR, SK, KN, AS...) : NON
INCLUS à cette étape, volontairement. Un prosigne combine plusieurs
lettres SANS l'espace inter-lettre habituel (ex. SK s'envoie comme un
seul groupe continu "...-.-", pas comme "S" puis "K" séparés) — cela
demande un traitement dédié dans MorseEncoder, pas une simple entrée
supplémentaire dans ce dictionnaire. Extension future documentée, pas
un oubli.
"""

from __future__ import annotations

MORSE_TABLE: dict[str, str] = {
    # Lettres
    "A": ".-",
    "B": "-...",
    "C": "-.-.",
    "D": "-..",
    "E": ".",
    "F": "..-.",
    "G": "--.",
    "H": "....",
    "I": "..",
    "J": ".---",
    "K": "-.-",
    "L": ".-..",
    "M": "--",
    "N": "-.",
    "O": "---",
    "P": ".--.",
    "Q": "--.-",
    "R": ".-.",
    "S": "...",
    "T": "-",
    "U": "..-",
    "V": "...-",
    "W": ".--",
    "X": "-..-",
    "Y": "-.--",
    "Z": "--..",
    # Chiffres
    "0": "-----",
    "1": ".----",
    "2": "..---",
    "3": "...--",
    "4": "....-",
    "5": ".....",
    "6": "-....",
    "7": "--...",
    "8": "---..",
    "9": "----.",
    # Ponctuation standard (code Morse international)
    ".": ".-.-.-",
    ",": "--..--",
    "?": "..--..",
    "'": ".----.",
    "!": "-.-.--",
    "/": "-..-.",
    "(": "-.--.",
    ")": "-.--.-",
    "&": ".-...",
    ":": "---...",
    ";": "-.-.-.",
    "=": "-...-",
    "+": ".-.-.",
    "-": "-....-",
    "_": "..--.-",
    '"': ".-..-.",
    "$": "...-..-",
    "@": ".--.-.",
}
