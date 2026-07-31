"""
ON3RT Radio Suite
libraries/voice/radio_phonetics.py

Épellation d'un indicatif (ou de tout texte alphanumérique) selon
l'alphabet radio international (OACI/OTAN) — "ON3RT" devient "Oscar
November Trois Roméo Tango" en français, "Oscar November Three Romeo
Tango" en anglais — pour que la synthèse vocale prononce correctement
un indicatif au lieu de le lire comme un mot ordinaire.

Diagnostic à l'origine de ce module (vérifié empiriquement, pas
deviné) : espeak-ng, utilisé par Piper pour la phonétisation, lit
"ON3RT" en interprétant "ON" comme le mot français courant "on" (le
pronom, prononcé /ɔ̃/) plutôt que comme deux lettres épelées.
`voice.phonemize("ON3RT")` confirme le problème ; `voice.phonemize(
"Oscar November Trois Roméo Tango")` confirme que la version épelée se
phonétise correctement, chaque mot étant un vrai mot du dictionnaire de
la langue.

Totalement indépendant du moteur de synthèse : ce module ne connaît ni
VoiceService, ni Pyttsx3Engine, ni PiperEngine — aucun import vers
libraries/voice/voice_service.py ni libraries/voice/engines.py. C'est
une transformation de texte pure, à appliquer par l'appelant AVANT de
fournir le texte à synthesize() ; elle profite donc identiquement à
pyttsx3, à Piper, et à tout futur moteur, sans qu'aucun d'eux n'ait à
la connaître.

Aucune modification du texte affiché : ce module ne touche jamais aux
modèles de message ni à l'interface (%CALL% reste "ON3RT" partout où
il est affiché/enregistré) — seule une copie transformée, destinée
uniquement à la synthèse, est produite par to_phonetic_spelling(). À
l'appelant (une étape ultérieure, pas ce module) de décider où
appliquer cette transformation avant l'appel à synthesize().

Deux tables complètes et indépendantes par langue (FR/EN), plutôt
qu'une table dérivée avec des exceptions : certains mots de l'alphabet
international officiel (basé sur l'anglais) ne se prononcent pas
naturellement en français sans une orthographe adaptée — ex. "Roméo"
(accent), "Hôtel" (accent), "Québec" (accent), "Juliette"/"Zoulou"
(orthographe francisée), "Whisky" (sans le "e" final). Ces choix
visent une PRONONCIATION correcte par le moteur, pas la pureté de
l'orthographe OTAN officielle. "X-ray" (lettre X) n'a pas d'équivalent
français naturel et reste tel quel dans les deux tables — sa
prononciation réelle via Piper/pyttsx3 reste à vérifier à l'oreille,
comme le reste de ce module, avant tout usage en production.

_LETTERS_FR["N"] = "Novembre" (jamais "November", contrairement à
_LETTERS_EN) : diagnostic empirique (voir historique de conception) —
espeak-ng, lisant le mot anglais "November" comme du texte français,
applique la règle française "finale -er se prononce /e/" (comme les
verbes du 1ᵉʳ groupe), avalant le "r" final. Le mot se termine alors
sur une voyelle accentuée isolée juste avant la pause qui précède le
mot suivant — un artefact acoustique perçu à l'oreille comme le mot
français "et" intercalé entre les deux mots (lui-même une simple
voyelle /e/). "Novembre" (le vrai mot français du mois) se termine par
un phonème consonne ("ʁ", le "r" français) plutôt qu'une voyelle
isolée, ce qui supprime cet artefact — confirmé par écoute comparative
réelle de plusieurs variantes (November/Novembre/Novembeur/Novembère)
sur le modèle fr_FR-tom-medium, "Novembre" retenue comme la plus
naturelle. _LETTERS_EN["N"] reste "November" : l'anglais ne connaît
pas cette règle de prononciation, aucun artefact équivalent constaté.

Langue non reconnue : repli sur la table anglaise (alphabet
international par défaut), jamais d'exception — cohérent avec le reste
de la Suite ("jamais une erreur qui bloquerait l'appelant").

Suffixes radio (/P, /M, /MM, /A...) : architecture prête à les
recevoir dès maintenant, traitement complet DÉLIBÉRÉMENT reporté à une
étape ultérieure (aucune valeur devinée aujourd'hui, aucune table de
suffixes remplie). Le texte est scindé en indicatif de base et suffixe
au premier "/" rencontré (jamais une suppression systématique du "/"
et de ce qui suit : le suffixe reste un concept explicite, pas du
bruit ignoré). Tant qu'un suffixe donné n'a pas d'entrée dans
_SUFFIX_WORDS_FR/_SUFFIX_WORDS_EN (aujourd'hui : aucune), il est épelé
lettre par lettre comme le reste de l'indicatif — comportement
identique à aujourd'hui, mais via un chemin de code déjà structuré pour
qu'ajouter une entrée plus tard (ex. "MM" -> "Maritime Mobile") ne
demande qu'une ligne dans la table, jamais une réécriture de
to_phonetic_spelling().

Caractères non reconnus (espace, tiret, tout ce qui n'est ni une
lettre ni un chiffre des tables) : ignorés silencieusement, jamais lus
tels quels. Insensible à la casse.
"""

from __future__ import annotations

# ------------------------------------------------------------------
# Alphabet radio international -- une table complète par langue,
# jamais une dérivation avec exceptions (voir docstring du module).
# ------------------------------------------------------------------

_LETTERS_FR: dict[str, str] = {
    "A": "Alpha",
    "B": "Bravo",
    "C": "Charlie",
    "D": "Delta",
    "E": "Echo",
    "F": "Foxtrot",
    "G": "Golf",
    "H": "Hôtel",
    "I": "India",
    "J": "Juliette",
    "K": "Kilo",
    "L": "Lima",
    "M": "Mike",
    "N": "Novembre",
    "O": "Oscar",
    "P": "Papa",
    "Q": "Québec",
    "R": "Roméo",
    "S": "Sierra",
    "T": "Tango",
    "U": "Uniform",
    "V": "Victor",
    "W": "Whisky",
    "X": "X-ray",
    "Y": "Yankee",
    "Z": "Zoulou",
}

_LETTERS_EN: dict[str, str] = {
    "A": "Alpha",
    "B": "Bravo",
    "C": "Charlie",
    "D": "Delta",
    "E": "Echo",
    "F": "Foxtrot",
    "G": "Golf",
    "H": "Hotel",
    "I": "India",
    "J": "Juliet",
    "K": "Kilo",
    "L": "Lima",
    "M": "Mike",
    "N": "November",
    "O": "Oscar",
    "P": "Papa",
    "Q": "Quebec",
    "R": "Romeo",
    "S": "Sierra",
    "T": "Tango",
    "U": "Uniform",
    "V": "Victor",
    "W": "Whiskey",
    "X": "X-ray",
    "Y": "Yankee",
    "Z": "Zulu",
}

_DIGITS_FR: dict[str, str] = {
    "0": "Zéro",
    "1": "Un",
    "2": "Deux",
    "3": "Trois",
    "4": "Quatre",
    "5": "Cinq",
    "6": "Six",
    "7": "Sept",
    "8": "Huit",
    "9": "Neuf",
}

_DIGITS_EN: dict[str, str] = {
    "0": "Zero",
    "1": "One",
    "2": "Two",
    "3": "Three",
    "4": "Four",
    "5": "Five",
    "6": "Six",
    "7": "Seven",
    "8": "Eight",
    "9": "Nine",
}

# ------------------------------------------------------------------
# Suffixes radio courants (/P, /M, /MM, /A...) -- volontairement VIDES
# à cette étape (voir docstring du module, section "Suffixes radio") :
# l'architecture reconnaît déjà un suffixe comme un concept à part
# entière, mais aucun mot n'est encore choisi pour eux. Tant qu'une clé
# donnée est absente d'ici, le suffixe correspondant est épelé lettre
# par lettre, comme aujourd'hui.
# ------------------------------------------------------------------

_SUFFIX_WORDS_FR: dict[str, str] = {}

_SUFFIX_WORDS_EN: dict[str, str] = {}


def _tables_for_language(language: str | None) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """Repli sur l'anglais si la langue n'est pas reconnue -- jamais d'exception."""

    code = (language or "").strip().upper()[:2]

    if code == "FR":
        return _LETTERS_FR, _DIGITS_FR, _SUFFIX_WORDS_FR

    return _LETTERS_EN, _DIGITS_EN, _SUFFIX_WORDS_EN


def _spell_word(word: str, letters: dict[str, str], digits: dict[str, str]) -> str:
    """Épelle `word` caractère par caractère ; ignore silencieusement tout caractère non reconnu."""

    spelled = []

    for char in word.upper():
        if char in letters:
            spelled.append(letters[char])
        elif char in digits:
            spelled.append(digits[char])
        # Caractère non reconnu (espace, tiret...) : ignoré, jamais lu tel quel.

    return " ".join(spelled)


def _split_suffix(text: str) -> tuple[str, str]:
    """
    Sépare `text` en (indicatif de base, suffixe) au premier "/"
    rencontré -- jamais une suppression du "/" : le suffixe reste un
    concept explicite (voir docstring du module), même si son
    traitement complet est encore reporté.
    """

    base, _separator, suffix = text.partition("/")
    return base, suffix


def to_phonetic_spelling(text: str, language: str = "FR") -> str:
    """
    Épelle `text` selon l'alphabet radio international, dans la langue
    donnée ("FR" ou "EN" ; toute autre valeur retombe sur l'anglais).
    Un éventuel suffixe (après un "/") est traité séparément -- voir
    docstring du module, section "Suffixes radio". Transformation pure,
    indépendante de tout moteur de synthèse.
    """

    letters, digits, suffix_words = _tables_for_language(language)

    base, suffix = _split_suffix(text)

    words = [_spell_word(base, letters, digits)]

    if suffix:
        suffix_word = suffix_words.get(suffix.strip().upper())
        words.append(suffix_word if suffix_word is not None else _spell_word(suffix, letters, digits))

    return " ".join(word for word in words if word)
