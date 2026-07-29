#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
ON3RT RADIO SUITE — Thème graphique officiel
Version : 2.0.0
Auteur : ON3RT
Description :
    Module unique et autonome portant toute l'identité visuelle
    de ON3RT LIVE : jetons de style (couleurs, polices, tailles,
    espacements, rayons, ombres, halos) et composants graphiques
    réutilisables (header, logo, titres, voyants, panneaux,
    cartes, horloge, badges, pastilles d'état, séparateurs).

    Conçu pour être repris tel quel comme thème commun des autres
    applications de la suite (Contest, Logbook, Radio Control,
    DX Cluster, Scanner...) : aucune dépendance à une logique
    métier ou à un service particulier, uniquement de la
    présentation.

    Règle d'or : aucune couleur, police, taille ou effet ne doit
    être écrit en dur en dehors de ce fichier — tout passe par les
    jetons et fonctions ci-dessous.
=========================================================
"""

from pathlib import Path

from PySide6.QtCore import Property, QEasingCurve, QPointF, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# =======================================================================
# 1. RESSOURCES
# =======================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGO_FILE = PROJECT_ROOT / "assets" / "logos" / "on3rt_logo_compact.png"

# Le fichier source encadre le blason d'une large marge transparente
# (bannière verticale prévue pour d'autres usages). On recadre sur le
# contenu réel (anneaux, pylône, globe, sigle) pour l'afficher en
# grand format dans le header sans agrandir du vide : (x, y, w, h).
LOGO_CROP_RECT = (100, 310, 815, 890)


# =======================================================================
# 2. JETONS DE STYLE (design tokens)
# =======================================================================

# ---- Couleurs ---------------------------------------------------------
# Bleu nuit / bleu électrique / cyan. Le vert et le rouge restent
# réservés aux états sémantiques (connecté / TX / alarme). Le logo
# ON3RT, avec son vert caractéristique, n'est jamais recoloré.

BG_VOID = "#050911"
BG_HEADER = "#0a1122"
BG_HEADER_2 = "#101d36"
BG_PANEL = "#0a1428"
BG_PANEL_2 = "#0d1a32"
BG_PILL = "#0f213d"

BORDER = "#1a2c4d"
BORDER_STRONG = "#2c4a78"

ACCENT = "#3b7bf5"
ACCENT_CYAN = "#22d3ee"
ACCENT_CYAN_DEEP = "#0c94a8"

TEXT_PRIMARY = "#edf2fb"
TEXT_SECONDARY = "#8ea1c4"
TEXT_MUTED = "#4f6288"

STATE_GREEN = "#2ed17e"
STATE_RED = "#f0464f"
STATE_AMBER = "#e8a63d"
STATE_INACTIVE = "#3a4a68"

# ---- Typographie --------------------------------------------------------

FONT_FAMILY = "Segoe UI"
FONT_FAMILY_MONO = "Consolas"

FONT_SIZE_BRAND = 22
FONT_SIZE_TAGLINE = 11
FONT_SIZE_PANEL_TITLE = 13
FONT_SIZE_BODY = 13
FONT_SIZE_SMALL = 11
FONT_SIZE_CAPTION = 9

# ---- Rayons / bordures --------------------------------------------------

RADIUS_LG = 14
RADIUS_MD = 10
RADIUS_SM = 6

# ---- Espacements ----------------------------------------------------------

SPACING_LG = 18
SPACING_MD = 14
SPACING_SM = 8

# ---- Gabarits de composants ------------------------------------------------

HEADER_HEIGHT = 136
HEADER_LOGO_HEIGHT = 80
LOGO_HALO_PADDING = 16

PILL_HEIGHT = 40
SEPARATOR_HEIGHT = 28

PANEL_TITLE_HEIGHT = 44
PANEL_CONTENT_MARGINS = (16, 14, 16, 16)
PANEL_CONTENT_SPACING = 10

# ---- Composants avancés de panneau (stats, tableaux, jauges) ------------

FONT_SIZE_HERO = 30
ICON_SIZE_LG = 30
PROGRESS_TRACK_HEIGHT = 6
TABLE_ROW_SPACING = 6
BAND_INDICATOR_ANIM_MS = 400

# ---- Ombres / halos ---------------------------------------------------------
# Volontairement discrets : l'interface doit rester confortable à
# l'œil sur de longues sessions, pas spectaculaire.

SHADOW_PANEL_BLUR = 22
SHADOW_PANEL_OFFSET_Y = 4
SHADOW_PANEL_ALPHA = 100

SHADOW_LOGO_BLUR = 18
SHADOW_LOGO_OFFSET_Y = 2
SHADOW_LOGO_ALPHA = 80

GLOW_LED_BLUR = 8
GLOW_LED_ALPHA = 150

HALO_LOGO_INNER_ALPHA = 45
HALO_LOGO_MID_ALPHA = 12

TRANSPARENT_QSS = "background:transparent; border:none;"


# =======================================================================
# 3. UTILITAIRES INTERNES
# =======================================================================

def _hex_to_rgb(hex_color):
    """Convertit une couleur '#rrggbb' du thème en triplet (r, g, b)."""

    hex_color = hex_color.lstrip("#")

    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _hex_to_rgba(hex_color, alpha):
    """Convertit une couleur '#rrggbb' du thème en chaîne rgba() QSS."""

    r, g, b = _hex_to_rgb(hex_color)

    return f"rgba({r}, {g}, {b}, {alpha})"


def _apply_shadow(widget, blur, offset_y, color_hex, alpha, offset_x=0):
    """Attache une ombre portée douce et paramétrée à un widget."""

    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(offset_x, offset_y)
    effect.setColor(QColor(*_hex_to_rgb(color_hex), alpha))
    widget.setGraphicsEffect(effect)

    return effect


# =======================================================================
# 4. FEUILLES DE STYLE (QSS)
# =======================================================================

def main_window_qss():
    """Style de la fenêtre principale, du fond et des scrollbars."""

    return f"""
        QMainWindow {{
            background: {BG_VOID};
        }}

        QWidget {{
            background: {BG_VOID};
            color: {TEXT_PRIMARY};
            font-family: "{FONT_FAMILY}";
        }}

        QStatusBar {{
            background: {BG_HEADER};
            color: {TEXT_SECONDARY};
            border-top: 1px solid {BORDER};
        }}

        QScrollArea {{
            border: none;
            background: transparent;
        }}

        QScrollBar:vertical {{
            background: {BG_PANEL};
            width: 12px;
            margin: 0px;
            border-radius: {RADIUS_SM}px;
        }}

        QScrollBar::handle:vertical {{
            background: {BORDER_STRONG};
            border-radius: {RADIUS_SM}px;
            min-height: 24px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: {ACCENT_CYAN_DEEP};
        }}

        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
            width: 0px;
            background: transparent;
            border: none;
        }}

        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: transparent;
        }}

        QScrollBar:horizontal {{
            background: {BG_PANEL};
            height: 12px;
            margin: 0px;
            border-radius: {RADIUS_SM}px;
        }}

        QScrollBar::handle:horizontal {{
            background: {BORDER_STRONG};
            border-radius: {RADIUS_SM}px;
            min-width: 24px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background: {ACCENT_CYAN_DEEP};
        }}

        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            height: 0px;
            width: 0px;
            background: transparent;
            border: none;
        }}

        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: transparent;
        }}
    """


def header_frame_qss():
    """Style du bandeau d'en-tête (dégradé + ligne d'accent basse)."""

    return f"""
        QFrame#HeaderBar {{
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 {BG_HEADER},
                stop:0.5 {BG_HEADER_2},
                stop:1 {BG_HEADER}
            );
            border: none;
            border-bottom: 2px solid {ACCENT_CYAN_DEEP};
        }}
    """


def panel_frame_qss():
    """
    Style unique pour tous les panneaux et cartes (contenu réel ou
    emplacements réservés) : même fond, même bordure, mêmes coins
    arrondis, avec un léger rehaut sur la bordure supérieure pour
    donner du relief.
    """

    return f"""
        QFrame#PanelFrame, QWidget#PanelFrame {{
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 {BG_PANEL_2},
                stop:1 {BG_PANEL}
            );
            border: 1px solid {BORDER};
            border-top: 1px solid {BORDER_STRONG};
            border-radius: {RADIUS_LG}px;
        }}
    """


def panel_title_bar_qss():
    """Style du bandeau de titre, identique pour tous les panneaux."""

    return f"""
        QWidget#PanelTitleBar {{
            background: {BG_PANEL_2};
            border-top-left-radius: {RADIUS_LG}px;
            border-top-right-radius: {RADIUS_LG}px;
            border-bottom: 1px solid {BORDER};
        }}
    """


def state_pill_qss(active):
    """Style de la pastille d'état radio (connecté / déconnecté)."""

    color = STATE_GREEN if active else STATE_RED

    return f"""
        background: {BG_PILL};
        color: {color};
        font-size: {FONT_SIZE_BODY}pt;
        font-weight: 600;
        padding: 0px 16px;
        border: 1px solid {BORDER_STRONG};
        border-radius: {RADIUS_MD}px;
    """


def clock_qss():
    """Style de l'horloge UTC (badge assorti à la pastille d'état)."""

    return f"""
        color: {ACCENT_CYAN};
        background: {BG_PILL};
        border: 1px solid {BORDER_STRONG};
        border-radius: {RADIUS_MD}px;
        padding: 0px 14px;
    """


def status_group_qss():
    """Style du regroupement des voyants réservés (chip unique)."""

    return f"""
        QFrame#StatusGroup {{
            background: {BG_PILL};
            border: 1px solid {BORDER_STRONG};
            border-radius: {RADIUS_MD}px;
        }}
    """


def accent_badge_qss():
    """
    Style d'un badge accent plein (ex. mode radio) : plus affirmé
    qu'un badge discret, pour mettre en valeur une valeur clé d'un
    panneau sans recourir à une couleur nouvelle.
    """

    return f"""
        color: {ACCENT_CYAN};
        background: {BG_PILL};
        border: 1px solid {BORDER_STRONG};
        border-radius: {RADIUS_SM}px;
        padding: 2px 14px;
        font-size: {FONT_SIZE_BODY}pt;
        font-weight: 700;
        letter-spacing: 1px;
    """


def badge_qss(color):
    """Style générique d'un badge/tag discret (texte + liseré coloré)."""

    return f"""
        color: {color};
        background: {BG_PILL};
        border: 1px solid {_hex_to_rgba(color, 90)};
        border-radius: {RADIUS_SM}px;
        padding: 2px 8px;
        font-size: {FONT_SIZE_CAPTION}pt;
        font-weight: 600;
    """


def info_row_qss():
    """Style des lignes d'information (labels de contenu des panneaux)."""

    return (
        f"font-size:{FONT_SIZE_BODY}pt; color:{TEXT_SECONDARY}; {TRANSPARENT_QSS}"
    )


def value_text_qss():
    """
    Style d'une valeur mise en avant (texte clair, gras) — utilisé
    par make_info_pair() et par toute valeur de tableau/jauge que
    l'on veut distinguer du texte secondaire.
    """

    return (
        f"color:{TEXT_PRIMARY}; font-size:{FONT_SIZE_BODY}pt; font-weight:600; "
        f"{TRANSPARENT_QSS}"
    )


def caption_qss():
    """Style des légendes secondaires discrètes."""

    return (
        f"font-size:{FONT_SIZE_CAPTION}pt; color:{TEXT_MUTED}; {TRANSPARENT_QSS}"
    )


# =======================================================================
# 5. COMPOSANTS — Header & identité (logo, titre)
# =======================================================================

def make_header_frame():
    """
    Construit le bandeau d'en-tête (fond, hauteur, marges) et renvoie
    son layout horizontal déjà configuré. L'appelant n'a plus qu'à y
    ajouter ses widgets, dans l'ordre voulu.
    """

    header = QFrame()
    header.setObjectName("HeaderBar")
    header.setStyleSheet(header_frame_qss())
    header.setFixedHeight(HEADER_HEIGHT)

    layout = QHBoxLayout(header)
    layout.setContentsMargins(SPACING_LG, 10, SPACING_LG, 10)
    layout.setSpacing(SPACING_MD)

    return header, layout


def load_logo_pixmap(height):
    """
    Charge le logo ON3RT, recadré sur son contenu réel (voir
    LOGO_CROP_RECT) et redimensionné en conservant la transparence
    et les proportions.

    Le pixmap est rendu à la résolution physique de l'écran (via son
    devicePixelRatio) puis marqué comme tel, afin d'éviter le lissage
    flou que Qt applique par défaut aux images 1x sur un écran mis à
    l'échelle (125 %, 150 %...).
    """

    raw = QPixmap(str(LOGO_FILE))

    if raw.isNull():
        return raw

    x, y, w, h = LOGO_CROP_RECT
    cropped = raw.copy(x, y, w, h)

    screen = QGuiApplication.primaryScreen()
    dpr = screen.devicePixelRatio() if screen else 1.0

    physical_height = max(1, round(height * dpr))

    scaled = cropped.scaledToHeight(
        physical_height, Qt.TransformationMode.SmoothTransformation
    )
    scaled.setDevicePixelRatio(dpr)

    return scaled


def make_header_logo():
    """
    Bloc logo du header : halo cyan très discret en arrière-plan,
    ombre légère pour la profondeur, logo net au premier plan.
    Élément d'identité principal de l'application.
    """

    pixmap = load_logo_pixmap(HEADER_LOGO_HEIGHT)

    side = HEADER_LOGO_HEIGHT + LOGO_HALO_PADDING * 2

    container = QWidget()
    container.setFixedSize(side, side)
    container.setStyleSheet(TRANSPARENT_QSS)

    halo = QLabel(container)
    halo.setGeometry(0, 0, side, side)
    halo.setStyleSheet(f"""
        background: qradialgradient(
            cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
            stop:0 {_hex_to_rgba(ACCENT_CYAN, HALO_LOGO_INNER_ALPHA)},
            stop:0.55 {_hex_to_rgba(ACCENT_CYAN, HALO_LOGO_MID_ALPHA)},
            stop:1 {_hex_to_rgba(ACCENT_CYAN, 0)}
        );
        border-radius: {side // 2}px;
        border: none;
    """)

    logo = QLabel(container)
    logo.setStyleSheet(TRANSPARENT_QSS)

    if not pixmap.isNull():
        logical_size = pixmap.deviceIndependentSize().toSize()
        logo.setPixmap(pixmap)
        logo.setFixedSize(logical_size)
        logo.move(
            (side - logical_size.width()) // 2,
            (side - logical_size.height()) // 2,
        )

    _apply_shadow(
        container, SHADOW_LOGO_BLUR, SHADOW_LOGO_OFFSET_Y, BG_VOID, SHADOW_LOGO_ALPHA
    )

    return container


def make_brand_title(module_name, brand="ON3RT"):
    """
    Bloc titre à deux niveaux : la marque ON3RT en grand (signature
    commune à toute la suite), et le nom du module en dessous, plus
    petit et espacé — ex. "LIVE", "CONTEST", "LOGBOOK". Permet de
    réutiliser exactement le même bloc dans chaque application de la
    suite en ne changeant que ce paramètre.
    """

    block = QWidget()
    block.setStyleSheet(TRANSPARENT_QSS)

    # Pile serrée, centrée verticalement dans tout l'espace que le
    # header lui accorde : les stretchs de part et d'autre absorbent
    # l'excédent, au lieu de laisser les labels eux-mêmes s'étirer.
    layout = QVBoxLayout(block)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)

    brand_label = QLabel(brand)
    brand_font = QFont(FONT_FAMILY)
    brand_font.setPointSize(FONT_SIZE_BRAND)
    brand_font.setBold(True)
    brand_label.setFont(brand_font)
    brand_label.setStyleSheet(
        f"color:{ACCENT_CYAN}; letter-spacing:2px; {TRANSPARENT_QSS}"
    )
    brand_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    tagline = QLabel(module_name)
    tagline_font = QFont(FONT_FAMILY)
    tagline_font.setPointSize(FONT_SIZE_TAGLINE)
    tagline_font.setBold(True)
    tagline.setFont(tagline_font)
    tagline.setStyleSheet(
        f"color:{TEXT_SECONDARY}; letter-spacing:5px; {TRANSPARENT_QSS}"
    )
    tagline.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

    layout.addStretch()
    layout.addWidget(brand_label)
    layout.addWidget(tagline)
    layout.addStretch()

    return block


def make_separator():
    """Séparateur vertical discret, notamment pour le bandeau d'en-tête."""

    line = QFrame()
    line.setFrameShape(QFrame.Shape.VLine)
    line.setFixedHeight(SEPARATOR_HEIGHT)
    line.setStyleSheet(
        f"color:{BORDER_STRONG}; background:{BORDER_STRONG}; max-width:1px; border:none;"
    )

    return line


# =======================================================================
# 6. COMPOSANTS — Voyants d'état
# =======================================================================

def make_status_led(label_text, state="inactive"):
    """
    Voyant d'état pour une intégration (CAT / DX Cluster / WSJT-X /
    Internet, etc.) : LED ronde avec halo de couleur + libellé
    discret. `state` ∈ {"inactive", "ok", "warning", "error"}.

    Tant qu'aucun service correspondant n'est réellement branché,
    l'état doit rester "inactive" (gris) : ce composant ne fait
    qu'afficher l'état qu'on lui donne, il n'en invente aucun.
    """

    color = {
        "inactive": STATE_INACTIVE,
        "ok": STATE_GREEN,
        "warning": STATE_AMBER,
        "error": STATE_RED,
    }.get(state, STATE_INACTIVE)

    holder = QWidget()
    holder.setStyleSheet(TRANSPARENT_QSS)

    layout = QHBoxLayout(holder)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(7)

    led = QLabel()
    led.setFixedSize(9, 9)
    led.setStyleSheet(f"""
        background: {color};
        border-radius: 4px;
        border: 1px solid {_hex_to_rgba(color, 110)};
    """)

    _apply_shadow(led, GLOW_LED_BLUR, 0, color, GLOW_LED_ALPHA)

    text = QLabel(label_text)
    text.setStyleSheet(
        f"color:{TEXT_MUTED}; font-size:{FONT_SIZE_CAPTION}pt; font-weight:600; "
        f"letter-spacing:1px; {TRANSPARENT_QSS}"
    )

    layout.addWidget(led)
    layout.addWidget(text)

    return holder


def make_status_group(items):
    """
    Regroupe plusieurs voyants (make_status_led) dans un même bandeau
    discret, pour la lisibilité et une meilleure utilisation de
    l'espace (un seul bloc au lieu de plusieurs éléments épars).

    `items` : liste de tuples (label, state).
    """

    frame = QFrame()
    frame.setObjectName("StatusGroup")
    frame.setStyleSheet(status_group_qss())
    frame.setFixedHeight(PILL_HEIGHT)

    layout = QHBoxLayout(frame)
    layout.setContentsMargins(14, 0, 14, 0)
    layout.setSpacing(SPACING_MD)

    for label, state in items:
        layout.addWidget(make_status_led(label, state))

    return frame


# =======================================================================
# 7. COMPOSANTS — Pastilles, badges, horloge
# =======================================================================

def make_state_pill(active=False, online_text="🟢 RADIO ONLINE", offline_text="🔴 RADIO OFFLINE"):
    """
    Pastille d'état binaire (ex. RADIO ONLINE / OFFLINE), prête à
    l'emploi. L'appelant met ensuite à jour son texte et son style
    via `state_pill_qss()` au fil des changements d'état réels.
    """

    label = QLabel(online_text if active else offline_text)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setFixedHeight(PILL_HEIGHT)
    label.setStyleSheet(state_pill_qss(active))

    return label


def make_clock_label():
    """Horloge UTC prête à l'emploi (police mono, badge assorti)."""

    label = QLabel()
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setFixedHeight(PILL_HEIGHT)

    font = QFont(FONT_FAMILY_MONO)
    font.setPointSize(FONT_SIZE_BODY)
    font.setBold(True)
    label.setFont(font)

    label.setStyleSheet(clock_qss())

    return label


def make_caption_label(text):
    """Légende discrète prête à l'emploi (ex. numéro de version)."""

    label = QLabel(text)
    label.setStyleSheet(caption_qss())

    return label


def make_badge(text, color=None):
    """Badge/tag générique discret, réutilisable pour tout libellé bref."""

    label = QLabel(text)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setStyleSheet(badge_qss(color or TEXT_SECONDARY))

    return label


# =======================================================================
# 8. COMPOSANTS — Panneaux & cartes
# =======================================================================

def apply_panel_frame(widget):
    """
    Applique le style de panneau unifié (fond, bordure, coins) et une
    ombre douce commune à un QFrame ou QWidget, pour une profondeur
    cohérente sur l'ensemble des panneaux de l'application.
    """

    widget.setObjectName("PanelFrame")
    widget.setStyleSheet(panel_frame_qss())

    _apply_shadow(
        widget, SHADOW_PANEL_BLUR, SHADOW_PANEL_OFFSET_Y, BG_VOID, SHADOW_PANEL_ALPHA
    )


def make_panel_title(text):
    """
    Bandeau de titre standard, strictement identique (hauteur,
    police, couleur, séparation) pour tous les panneaux du tableau
    de bord, y compris les cartes/emplacements réservés.
    """

    bar = QWidget()
    bar.setObjectName("PanelTitleBar")
    bar.setStyleSheet(panel_title_bar_qss())
    bar.setFixedHeight(PANEL_TITLE_HEIGHT)

    layout = QHBoxLayout(bar)
    layout.setContentsMargins(SPACING_MD, 0, SPACING_MD, 0)

    label = QLabel(text)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    font = QFont(FONT_FAMILY)
    font.setPointSize(FONT_SIZE_PANEL_TITLE)
    font.setBold(True)
    label.setFont(font)

    label.setStyleSheet(
        f"color:{ACCENT_CYAN}; letter-spacing:1px; {TRANSPARENT_QSS}"
    )

    layout.addWidget(label)

    return bar


class RadarBackdrop(QWidget):
    """
    Fond décoratif très discret façon plan de couverture radio
    (anneaux + croisée). Purement visuel, ne représente aucune
    donnée réelle et ne gêne jamais la lecture du texte affiché
    par-dessus. Réutilisable pour toute carte à caractère "radio/
    carte/couverture" dans la suite (CARTE, DX Cluster, Scanner...).
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setStyleSheet(TRANSPARENT_QSS)

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2
        cy = h / 2
        max_radius = min(w, h) * 0.42

        ring_color = QColor(*_hex_to_rgb(ACCENT_CYAN))
        ring_color.setAlpha(16)

        pen = QPen(ring_color)
        pen.setWidthF(1.0)
        painter.setPen(pen)

        for i in (1, 2, 3):
            r = max_radius * i / 3
            painter.drawEllipse(QPointF(cx, cy), r, r)

        painter.drawLine(QPointF(cx - max_radius, cy), QPointF(cx + max_radius, cy))
        painter.drawLine(QPointF(cx, cy - max_radius), QPointF(cx, cy + max_radius))

        diag_color = QColor(*_hex_to_rgb(ACCENT_CYAN))
        diag_color.setAlpha(9)
        pen.setColor(diag_color)
        painter.setPen(pen)

        offset = max_radius * 0.7071

        painter.drawLine(
            QPointF(cx - offset, cy - offset), QPointF(cx + offset, cy + offset)
        )
        painter.drawLine(
            QPointF(cx - offset, cy + offset), QPointF(cx + offset, cy - offset)
        )

        painter.end()


def build_info_card(title, text="En construction", text_color=None, pattern=False, columns=None):
    """
    Carte d'information complète et prête à l'emploi : bandeau de
    titre + zone de contenu centrée, avec le style panneau unifié.
    Utilisée pour les emplacements encore réservés du tableau de
    bord (CARTE, DX CLUSTER, PROPAGATION, WSJT-X, MESSAGES...).

    `pattern=True` ajoute le fond décoratif RadarBackdrop, pour les
    cartes à thématique "couverture radio" (ex. CARTE).

    `columns` (optionnel) : liste de tuples (texte, stretch) — ajoute
    un en-tête de tableau "fantôme" (voir make_table_header), pour
    que la carte annonce déjà la forme de son futur contenu tabulaire
    (ex. DX CLUSTER, WSJT-X) sans qu'il soit nécessaire de revoir sa
    présentation une fois la fonctionnalité branchée.
    """

    text_color = text_color or TEXT_SECONDARY

    frame = QFrame()
    apply_panel_frame(frame)
    frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    layout = QVBoxLayout(frame)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.addWidget(make_panel_title(title))

    if pattern:
        body_widget = RadarBackdrop()
    else:
        body_widget = QWidget()
        body_widget.setStyleSheet(TRANSPARENT_QSS)

    body = QVBoxLayout(body_widget)
    body.setContentsMargins(*PANEL_CONTENT_MARGINS)
    body.setSpacing(PANEL_CONTENT_SPACING)
    layout.addWidget(body_widget, 1)

    if columns:
        body.addWidget(make_table_header(columns))

    label = QLabel(text)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setStyleSheet(
        f"color:{text_color}; font-size:{FONT_SIZE_SMALL}pt; {TRANSPARENT_QSS}"
    )

    body.addStretch()
    body.addWidget(label)
    body.addStretch()

    return frame


# =======================================================================
# 9. COMPOSANTS — Statistiques, tableaux, jauges
# =======================================================================
#
# Briques communes pour organiser les données d'un panneau en
# hiérarchie claire (valeur "hero" + légende, badge de mise en
# valeur, paires légende/valeur en grille, lignes de tableau
# alignées, jauge de progression décorative). Réutilisables par
# n'importe quel panneau de la suite.

def make_hero_caption(text):
    """Légende courte au-dessus d'une valeur "hero" (ex. FRÉQUENCE)."""

    label = QLabel(text)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setStyleSheet(
        f"color:{TEXT_MUTED}; font-size:{FONT_SIZE_CAPTION}pt; font-weight:600; "
        f"letter-spacing:2px; {TRANSPARENT_QSS}"
    )

    return label


def make_hero_value(initial_text="--"):
    """
    Valeur mise en avant (ex. fréquence, température) : grande,
    grasse, en police mono pour un rendu "afficheur d'appareil".
    """

    label = QLabel(initial_text)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    font = QFont(FONT_FAMILY_MONO)
    font.setPointSize(FONT_SIZE_HERO)
    font.setBold(True)
    label.setFont(font)

    label.setStyleSheet(f"color:{ACCENT_CYAN}; {TRANSPARENT_QSS}")

    return label


def make_accent_badge(initial_text="--"):
    """
    Badge plein pour une valeur clé à mettre en valeur (ex. mode
    radio). Voir accent_badge_qss().
    """

    label = QLabel(initial_text)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setStyleSheet(accent_badge_qss())

    return label


def make_icon_label(icon_text, size=ICON_SIZE_LG):
    """Icône (emoji) affichée en grand, pour donner un repère visuel immédiat."""

    label = QLabel(icon_text)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    font = QFont(FONT_FAMILY)
    font.setPointSize(size)
    label.setFont(font)

    label.setStyleSheet(TRANSPARENT_QSS)

    return label


def make_info_pair(caption_text, initial_value="--"):
    """
    Paire légende/valeur (ex. "BANDE" au-dessus de "20m"), pour
    organiser les données secondaires d'un panneau en grille plutôt
    qu'en longue liste de lignes "Label : valeur".

    Renvoie (widget_conteneur, label_valeur) : l'appelant conserve
    la référence à label_valeur pour la mettre à jour au fil des
    données réelles.
    """

    container = QWidget()
    container.setStyleSheet(TRANSPARENT_QSS)

    layout = QVBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)

    caption = QLabel(caption_text)
    caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
    caption.setStyleSheet(
        f"color:{TEXT_MUTED}; font-size:{FONT_SIZE_CAPTION}pt; font-weight:600; "
        f"letter-spacing:1px; {TRANSPARENT_QSS}"
    )

    value = QLabel(initial_value)
    value.setAlignment(Qt.AlignmentFlag.AlignCenter)
    value.setStyleSheet(value_text_qss())

    layout.addWidget(caption)
    layout.addWidget(value)

    return container, value


def make_table_header(columns):
    """
    En-tête de tableau discret, colonnes alignées. `columns` : liste
    de tuples (texte, stretch), ex. [("DATE", 1), ("INDICATIF", 2)].
    """

    row = QWidget()
    row.setStyleSheet(TRANSPARENT_QSS)

    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(SPACING_SM)

    for text, stretch in columns:
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            f"color:{TEXT_MUTED}; font-size:{FONT_SIZE_CAPTION}pt; font-weight:700; "
            f"letter-spacing:1px; {TRANSPARENT_QSS}"
        )
        layout.addWidget(label, stretch)

    return row


def make_table_row(values, emphasize_index=None):
    """
    Ligne de tableau alignée en colonnes, assortie à make_table_header.
    `values` : liste de tuples (texte, stretch). `emphasize_index` :
    index de la colonne à mettre en avant (ex. l'indicatif dans le
    logbook), affichée en clair et en gras plutôt qu'en texte discret.
    """

    row = QWidget()
    row.setStyleSheet(TRANSPARENT_QSS)

    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(SPACING_SM)

    for index, (text, stretch) in enumerate(values):
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if index == emphasize_index:
            label.setStyleSheet(
                f"color:{TEXT_PRIMARY}; font-size:{FONT_SIZE_BODY}pt; "
                f"font-weight:700; {TRANSPARENT_QSS}"
            )
        else:
            label.setStyleSheet(
                f"color:{TEXT_SECONDARY}; font-size:{FONT_SIZE_SMALL}pt; {TRANSPARENT_QSS}"
            )

        layout.addWidget(label, stretch)

    return row


class BandIndicator(QWidget):
    """
    Indicateur graphique réutilisable pour un niveau d'activité de
    0 à 100 % (ex. activité par bande) : piste + remplissage en
    dégradé dont la longueur reflète le niveau, avec une transition
    animée légère à chaque changement.

    Aujourd'hui utilisé en mode démonstration (niveau à 0, aucune
    donnée réelle affichée). Lorsque de vraies données d'activité
    seront disponibles, seul ce composant devra évoluer : les
    panneaux qui l'utilisent n'ont qu'à appeler set_level(valeur),
    sans jamais changer leur propre mise en page.
    """

    def __init__(self, height=PROGRESS_TRACK_HEIGHT, parent=None):
        super().__init__(parent)

        self._level = 0.0

        self.setFixedHeight(height)
        self.setMinimumWidth(30)
        self.setStyleSheet(TRANSPARENT_QSS)

        self._animation = QPropertyAnimation(self, b"level")
        self._animation.setDuration(BAND_INDICATOR_ANIM_MS)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    # ---- Propriété Qt "level" (0-100), animable ------------------------

    def _get_level(self):
        return self._level

    def _set_level(self, value):
        self._level = max(0.0, min(100.0, value))
        self.update()

    level = Property(float, _get_level, _set_level)

    # ---- API publique ---------------------------------------------------

    def set_level(self, percent, animate=True):
        """
        Définit le niveau d'activité affiché (0-100). En mode
        démonstration, laisser à 0 (valeur par défaut).
        """

        target = max(0.0, min(100.0, float(percent)))

        if animate:
            self._animation.stop()
            self._animation.setStartValue(self._level)
            self._animation.setEndValue(target)
            self._animation.start()
        else:
            self._set_level(target)

    # ---- Rendu ------------------------------------------------------------

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = rect.height() / 2

        painter.setPen(QPen(QColor(*_hex_to_rgb(BORDER)), 1))
        painter.setBrush(QColor(*_hex_to_rgb(BG_PILL)))
        painter.drawRoundedRect(rect, radius, radius)

        if self._level > 0:
            fill_width = max(rect.height(), rect.width() * (self._level / 100.0))

            fill_rect = QRectF(rect)
            fill_rect.setWidth(fill_width)

            gradient = QLinearGradient(fill_rect.topLeft(), fill_rect.topRight())
            gradient.setColorAt(0.0, QColor(*_hex_to_rgb(ACCENT_CYAN_DEEP)))
            gradient.setColorAt(1.0, QColor(*_hex_to_rgb(ACCENT_CYAN)))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(gradient)
            painter.drawRoundedRect(fill_rect, radius, radius)

        painter.end()
