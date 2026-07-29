"""
ON3RT Radio Suite
Palette de couleurs partagée.

Charte graphique commune à toutes les applications de la suite :
bleu nuit / noir / bleu électrique / cyan.

Le vert est réservé aux états connecté / actif / RX / OK.
Le rouge est réservé au TX / erreur / alarme.

Ce module est la source de vérité unique pour les couleurs, aussi bien
pour le QSS global (assets/themes/on3rt_dark.qss) que pour les widgets
dessinés au QPainter (libraries/ui/components/*).
"""

# ---------------------------------------------------------------------
# Surfaces
# ---------------------------------------------------------------------

BG_VOID = "#050911"
BG_HEADER = "#0a1122"
BG_PANEL = "#0a1428"
BG_PANEL_2 = "#0d1a32"
BG_CARD = "#0f1c36"
BG_CARD_HOVER = "#13233f"

# ---------------------------------------------------------------------
# Bordures
# ---------------------------------------------------------------------

BORDER = "#1a2c4d"
BORDER_SOFT = "rgba(255, 255, 255, 20)"
BORDER_STRONG = "#2c4a78"

# ---------------------------------------------------------------------
# Accents (identité ON3RT)
# ---------------------------------------------------------------------

ACCENT = "#3b7bf5"
ACCENT_CYAN = "#22d3ee"
ACCENT_CYAN_DEEP = "#0c94a8"

# ---------------------------------------------------------------------
# Texte
# ---------------------------------------------------------------------

TEXT_PRIMARY = "#edf2fb"
TEXT_SECONDARY = "#8ea1c4"
TEXT_MUTED = "#4f6288"

# ---------------------------------------------------------------------
# États sémantiques (usage restreint)
# ---------------------------------------------------------------------

STATE_GREEN = "#2ed17e"   # connecté / actif / RX / OK
STATE_RED = "#f0464f"     # TX / erreur / alarme
STATE_AMBER = "#e8a63d"   # avertissement (usage rare)
