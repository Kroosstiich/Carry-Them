"""Builds CarryThem.esp (ESL-flagged) from scratch.

Records (local FormIDs, also used by the OAR configs - keep them stable):
  0x800 QUST CT_Control          start-game-enabled; aliases Player (forced) and Passenger (optional)
  0x801 MGEF CT_HopOnEffect      script effect of the power (CT_HopOnEffect)
  0x802 SPEL CT_HopOnPower       lesser power, fire and forget, target actor
  0x803 MGEF CT_CarriedEffect    marker on the rider        -> OAR "rider" poses
  0x804 SPEL CT_CarriedAbility
  0x805 MGEF CT_CarryingEffect   marker on the player       -> OAR "carrier" pose
  0x806 SPEL CT_CarryingAbility
  0x807-0x809 GLOB CT_OffsetX / Y / Z   rider offset, tunable from the console and the MCM
  0x80A GLOB CT_Rotation         rider facing vs the player's, degrees (Piggyback >= 1.2.2)
  0x80B QUST CT_MCM              optional MCM (MCM Helper + SkyUI); inert when they are missing
  0x80C-0x80D                    unused (a second power in a 1.1.0 test build); do not reuse
  0x80E MGEF CT_PrincessCarriedEffect   marker on the rider    -> OAR "princess-rider" pose
  0x80F SPEL CT_PrincessCarriedAbility
  0x810 MGEF CT_PrincessCarryingEffect  marker on the player   -> OAR "princess-carrier" pose
  0x811 SPEL CT_PrincessCarryingAbility
  0x812-0x815 GLOB CT_PrincessOffsetX / Y / Z, CT_PrincessRotation
  0x816 MESG CT_StyleMenu        the power's menu: on the back / in the arms / cancel
  0x817 GLOB CT_Hotkey           optional key (DirectX scan code, -1 = none): carry the NPC in the crosshair
  0x818 GLOB CT_PromptEnabled    1 = the optional SkyPrompt prompt is shown (MCM toggle; read by CarryThem - SkyPrompt.esp)
Also builds the optional "CarryThem - Dialogue.esp" (see build_dialogue) with its SEQ file, and
"CarryThem - SkyPrompt.esp" (see build_skyprompt).
Usage: python build_plugin.py <output folder> [en|fr]   (language of the in-game texts, en by default)
"""
import os, struct, sys

PLUGIN = "CarryThem.esp"
OWN = 0x01000000                     # one master (Skyrim.esm) -> our records use index 01
QUEST, HOP_MGEF, HOP_SPEL, CARRIED_MGEF, CARRIED_SPEL, CARRYING_MGEF, CARRYING_SPEL = range(OWN | 0x800, OWN | 0x807)
OFFSET_X, OFFSET_Y, OFFSET_Z, ROTATION, MCM_QUEST = range(OWN | 0x807, OWN | 0x80C)
(P_CARRIED_MGEF, P_CARRIED_SPEL, P_CARRYING_MGEF, P_CARRYING_SPEL,
 P_OFFSET_X, P_OFFSET_Y, P_OFFSET_Z, P_ROTATION, STYLE_MENU, HOTKEY, PROMPT_ENABLED) = range(OWN | 0x80E, OWN | 0x819)
NEXT_OBJECT_ID = 0x819
OFFSET_DEFAULTS = (0.0, -35.0, -25.0)  # tuned in game (Carry Me's piggyback was 0, -30, 0)
ROTATION_DEFAULT = 10.0                # tuned in game: the pose faced slightly left
P_OFFSET_DEFAULTS = (30.0, 34.0, -10.0)  # Carry Me's bridal carry on the left forearm, Y and Z tuned in game (were 35, 15)
PLAYER_REF, ACTOR_TYPE_NPC, EQUIP_VOICE = 0x14, 0x13794, 0x25BEE
FLAG_ESL = 0x200

# In-game texts of the three plugins. The French plugins keep every FormID: the FOMOD swaps the files.
LANG = "en"
TEXT = {
    "en": {
        "power": "Carry Them", "power_desc": "Carry someone, on your back or in your arms. Jump to set them down.",
        "carried": "Being Carried", "carrying": "Carrying Someone",
        "carrying_back": "Your hands are busy holding someone on your back. Jump to set them down.",
        "carrying_arms": "Your hands are busy holding someone in your arms. Jump to set them down.",
        "menu": "How do you carry them?", "menu_back": "On my back", "menu_arms": "In my arms", "menu_cancel": "Cancel",
        "ask": "Let me carry you.", "how": "How?", "back": "On my back.", "arms": "In my arms.",
        "nevermind": "Never mind.", "ok": "All right.", "ok_nevermind": "Oh. All right.",
        "prompt_carry": "Carry", "prompt_drop": "Set down",
    },
    "fr": {
        "power": "Carry Them", "power_desc": "Portez quelqu'un sur le dos ou dans les bras. Sautez pour le reposer.",
        "carried": "Porté", "carrying": "Porte quelqu'un",
        "carrying_back": "Vos mains sont occupées à tenir quelqu'un sur votre dos. Sautez pour le reposer.",
        "carrying_arms": "Vos mains sont occupées à tenir quelqu'un dans vos bras. Sautez pour le reposer.",
        "menu": "Comment voulez-vous le porter ?", "menu_back": "Sur le dos", "menu_arms": "Dans les bras",
        "menu_cancel": "Annuler",
        "ask": "Laissez-moi vous porter.", "how": "Comment ?", "back": "Sur mon dos.", "arms": "Dans mes bras.",
        "nevermind": "Laissez tomber.", "ok": "D'accord.", "ok_nevermind": "Ah. D'accord.",
        "prompt_carry": "Porter", "prompt_drop": "Reposer",
    },
}


def t(key):
    return TEXT[LANG][key]


# Texts of the scripts' notifications and of the MCM, as "$key" strings that the game and MCM Helper look
# up in Interface\Translations\CarryThem_<GAME LANGUAGE>.txt. One file per game language, all in LANG:
# the language picked in the installer wins whatever the game's language.
TRANSLATIONS = {
    "en": {
        "$CT_NeedPiggyback": "Carry Them needs Piggyback 1.2.2 or later.",
        "$CT_CantCarryThat": "You can't carry that.",
        "$CT_WontLetYou": "They won't let you carry them now.",
        "$CT_SheatheFirst": "Sheathe your weapon first.",
        "$CT_CantCarryFromHere": "You can't carry anyone from here.",
        "$CT_NeedOMA": "Carry Them needs Offset Movement Animation (run Nemesis or Pandora).",
        "$CT_Controls": "Controls",
        "$CT_CarryKey": "Carry key",
        "$CT_CarryKeyHelp": "Look at someone and press it to pick them up (a menu asks how), press it again to set them down. Optional: the Carry Them power does the same.",
        "$CT_PromptToggle": "SkyPrompt prompt",
        "$CT_PromptToggleHelp": "Shows the prompt when you look at someone. Only if you picked the SkyPrompt option in the installer.",
        "$CT_BackPosition": "Piggyback position",
        "$CT_TakesEffect": "Takes effect the next time you pick someone up.",
        "$CT_Height": "Height",
        "$CT_HeightHelp": "Up and down. Lower it if the rider sits too high. Console: set CT_OffsetZ to <value>",
        "$CT_BackForward": "Back / forward",
        "$CT_BackForwardHelp": "More negative moves the rider further back. Console: set CT_OffsetY to <value>",
        "$CT_LeftRight": "Left / right",
        "$CT_LeftRightHelp": "Positive moves the rider to the right. Console: set CT_OffsetX to <value>",
        "$CT_Rotation": "Rotation",
        "$CT_RotationHelp": "Turns the rider, in degrees. Positive turns it to the right. Console: set CT_Rotation to <value>",
        "$CT_ArmsPosition": "Princess carry position",
        "$CT_ArmsHeightHelp": "Up and down. Console: set CT_PrincessOffsetZ to <value>",
        "$CT_ArmsBackForwardHelp": "More negative moves the rider closer to you. Console: set CT_PrincessOffsetY to <value>",
        "$CT_ArmsLeftRightHelp": "Positive moves the rider to the right. Console: set CT_PrincessOffsetX to <value>",
        "$CT_ArmsRotationHelp": "Turns the rider, in degrees. Positive turns it to the right. Console: set CT_PrincessRotation to <value>",
    },
    "fr": {
        "$CT_NeedPiggyback": "Carry Them nécessite Piggyback 1.2.2 ou une version plus récente.",
        "$CT_CantCarryThat": "Vous ne pouvez pas porter ça.",
        "$CT_WontLetYou": "Cette personne refuse d'être portée pour l'instant.",
        "$CT_SheatheFirst": "Rengainez d'abord votre arme.",
        "$CT_CantCarryFromHere": "Vous ne pouvez porter personne d'ici.",
        "$CT_NeedOMA": "Carry Them nécessite Offset Movement Animation (lancez Nemesis ou Pandora).",
        "$CT_Controls": "Commandes",
        "$CT_CarryKey": "Touche de portage",
        "$CT_CarryKeyHelp": "Regardez quelqu'un et appuyez sur cette touche pour le porter (un menu vous demande comment). Appuyez de nouveau pour le reposer. Facultatif : le pouvoir Carry Them fait la même chose.",
        "$CT_PromptToggle": "Invite SkyPrompt",
        "$CT_PromptToggleHelp": "Affiche l'invite quand vous regardez quelqu'un. Seulement si vous avez choisi l'option SkyPrompt dans l'installateur.",
        "$CT_BackPosition": "Position sur le dos",
        "$CT_TakesEffect": "S'applique la prochaine fois que vous portez quelqu'un.",
        "$CT_Height": "Hauteur",
        "$CT_HeightHelp": "Monte ou descend la personne portée. Baissez la valeur si elle est trop haute. Console : set CT_OffsetZ to <valeur>",
        "$CT_BackForward": "Arrière / avant",
        "$CT_BackForwardHelp": "Plus la valeur est négative, plus la personne portée recule. Console : set CT_OffsetY to <valeur>",
        "$CT_LeftRight": "Gauche / droite",
        "$CT_LeftRightHelp": "Une valeur positive décale la personne portée vers la droite. Console : set CT_OffsetX to <valeur>",
        "$CT_Rotation": "Rotation",
        "$CT_RotationHelp": "Fait pivoter la personne portée, en degrés. Une valeur positive la tourne vers la droite. Console : set CT_Rotation to <valeur>",
        "$CT_ArmsPosition": "Position dans les bras",
        "$CT_ArmsHeightHelp": "Monte ou descend la personne portée. Console : set CT_PrincessOffsetZ to <valeur>",
        "$CT_ArmsBackForwardHelp": "Plus la valeur est négative, plus la personne portée se rapproche de vous. Console : set CT_PrincessOffsetY to <valeur>",
        "$CT_ArmsLeftRightHelp": "Une valeur positive décale la personne portée vers la droite. Console : set CT_PrincessOffsetX to <valeur>",
        "$CT_ArmsRotationHelp": "Fait pivoter la personne portée, en degrés. Une valeur positive la tourne vers la droite. Console : set CT_PrincessRotation to <valeur>",
    },
}
GAME_LANGUAGES = ("ENGLISH", "FRENCH", "GERMAN", "ITALIAN", "SPANISH", "POLISH", "RUSSIAN", "JAPANESE", "CHINESE", "CZECH")


def translation_file():
    """Interface translation file: UTF-16 LE with a BOM, one "$key<TAB>text" per line."""
    text = "".join(f"{k}\t{v}\r\n" for k, v in TRANSLATIONS[LANG].items())
    return "\ufeff".encode("utf-16-le") + text.encode("utf-16-le")


def z(s):
    return s.encode("cp1252") + b"\0"


def sub(sig, data):
    return sig + struct.pack("<H", len(data)) + data


def record(sig, fid, subs):
    body = b"".join(sub(s, d) for s, d in subs)
    return sig + struct.pack("<IIIIHH", len(body), 0, fid, 0, 44, 0) + body


def group(sig, records, group_type=0):
    """sig is the label: a record type for a top group, a packed FormID for a topic's children (type 7)."""
    body = b"".join(records)
    return b"GRUP" + struct.pack("<I", 24 + len(body)) + sig + struct.pack("<iHHI", group_type, 0, 0, 0) + body


def header(count, next_id, desc, masters):
    head = b"".join(sub(s, d) for s, d in [
        # 1.70, not 1.71: 1.71 needs Skyrim 1.6.1130+ (or BEES), and our IDs (0x800+) fit 1.70 anyway.
        (b"HEDR", struct.pack("<fII", 1.70, count, next_id)), (b"CNAM", z("Kroosstii")), (b"SNAM", z(desc)),
    ] + [x for m in masters for x in ((b"MAST", z(m)), (b"DATA", b"\0" * 8))])
    return b"TES4" + struct.pack("<IIIIHH", len(head), FLAG_ESL, 0, 0, 44, 0) + head


# --- VMAD (version 5, object format 2) --------------------------------------------------------
def wstr(s):
    return struct.pack("<H", len(s)) + s.encode("ascii")


def prop(name, fid, alias=-1):
    return wstr(name) + struct.pack("<BBHhI", 1, 1, 0, alias, fid)   # type Object, status Edited


def script(name, props=()):
    return wstr(name) + struct.pack("<BH", 0, len(props)) + b"".join(props)


def scripts(*items):
    return struct.pack("<HHH", 5, 2, len(items)) + b"".join(items)


def quest_vmad(quest_scripts, aliases, quest=QUEST):
    out = scripts(*quest_scripts) + struct.pack("<BH", 2, 0) + wstr("") + struct.pack("<H", len(aliases))
    for alias_id, alias_scripts in aliases:
        out += struct.pack("<HhI", 0, alias_id, quest) + scripts(*alias_scripts)
    return out


# --- Magic effects and spells -------------------------------------------------------------------
# MGEF DATA, 38 fields / 152 bytes (UESP): flags, cost, related, skill, resist, counters, light,
# taper weight, hit/enchant shaders, skill level, area, casting time, taper curve/duration, 2nd AV
# weight, archetype, primary AV, projectile, explosion, casting type, delivery, 2nd AV, casting art,
# hit art, impact data, skill usage mult, dual cast art/scale, enchant art, hit/enchant visuals,
# equip ability, image space, perk, sound level, AI score, AI delay.
MGEF_DATA = "<IfIiiIIfIIIIffffIiIIIIiIIIfIfIIIIIIIff"
assert struct.calcsize(MGEF_DATA) == 152
ARCHETYPE_SCRIPT, CONSTANT, FIRE_AND_FORGET, SELF, TARGET_ACTOR = 1, 0, 1, 0, 3


def mgef(fid, edid, name, cast, delivery, vmad=None, desc=""):
    data = struct.pack(MGEF_DATA, 0, 0.0, 0, -1, -1, 0, 0, 0.0, 0, 0, 0, 0, 0.0, 0.0, 0.0, 0.0,
                       ARCHETYPE_SCRIPT, -1, 0, 0, cast, delivery, -1, 0, 0, 0, 1.0, 0, 1.0,
                       0, 0, 0, 0, 0, 0, 1, 0.0, 0.0)
    subs = [(b"EDID", z(edid))] + ([(b"VMAD", vmad)] if vmad else [])
    subs += [(b"FULL", z(name)), (b"DATA", data), (b"SNDD", b""), (b"DNAM", z(desc))]
    return record(b"MGEF", fid, subs)


SPELL_POWER_LESSER, SPELL_ABILITY = 3, 4


def spel(fid, edid, name, effect, spell_type, cast, delivery, desc="", spell_range=0.0):
    spit = struct.pack("<IIIfIIffI", 0, 0, spell_type, 0.0, cast, delivery, 0.0, spell_range, 0)
    return record(b"SPEL", fid, [
        (b"EDID", z(edid)), (b"OBND", b"\0" * 12), (b"FULL", z(name)),
        (b"ETYP", struct.pack("<I", EQUIP_VOICE)), (b"DESC", z(desc)), (b"SPIT", spit),
        (b"EFID", struct.pack("<I", effect)), (b"EFIT", struct.pack("<fII", 0.0, 0, 0)),
    ])


def glob(fid, edid, value):
    return record(b"GLOB", fid, [(b"EDID", z(edid)), (b"FNAM", b"f"), (b"FLTV", struct.pack("<f", value))])


def build():
    globs = [glob(fid, "CT_Offset" + axis, value)
             for fid, axis, value in zip((OFFSET_X, OFFSET_Y, OFFSET_Z), "XYZ", OFFSET_DEFAULTS)]
    globs.append(glob(ROTATION, "CT_Rotation", ROTATION_DEFAULT))
    globs += [glob(fid, "CT_PrincessOffset" + axis, value)
              for fid, axis, value in zip((P_OFFSET_X, P_OFFSET_Y, P_OFFSET_Z), "XYZ", P_OFFSET_DEFAULTS)]
    globs.append(glob(P_ROTATION, "CT_PrincessRotation", 0.0))
    globs.append(glob(HOTKEY, "CT_Hotkey", -1.0))
    globs.append(glob(PROMPT_ENABLED, "CT_PromptEnabled", 1.0))                     # -1: unbound (SkyUI shows 0 as a key)
    mgefs = [
        mgef(HOP_MGEF, "CT_HopOnEffect", t("power"), FIRE_AND_FORGET, TARGET_ACTOR,
             scripts(script("CT_HopOnEffect", [prop("Control", QUEST)]))),
        mgef(CARRIED_MGEF, "CT_CarriedEffect", t("carried"), CONSTANT, SELF),
        mgef(CARRYING_MGEF, "CT_CarryingEffect", t("carrying"), CONSTANT, SELF, desc=t("carrying_back")),
        mgef(P_CARRIED_MGEF, "CT_PrincessCarriedEffect", t("carried"), CONSTANT, SELF),
        mgef(P_CARRYING_MGEF, "CT_PrincessCarryingEffect", t("carrying"), CONSTANT, SELF, desc=t("carrying_arms")),
    ]
    spells = [
        spel(HOP_SPEL, "CT_HopOnPower", t("power"), HOP_MGEF, SPELL_POWER_LESSER, FIRE_AND_FORGET,
             TARGET_ACTOR, t("power_desc"), 5.0),
        spel(CARRIED_SPEL, "CT_CarriedAbility", t("carried"), CARRIED_MGEF, SPELL_ABILITY, CONSTANT, SELF),
        spel(CARRYING_SPEL, "CT_CarryingAbility", t("carrying"), CARRYING_MGEF, SPELL_ABILITY, CONSTANT, SELF),
        spel(P_CARRIED_SPEL, "CT_PrincessCarriedAbility", t("carried"), P_CARRIED_MGEF, SPELL_ABILITY, CONSTANT, SELF),
        spel(P_CARRYING_SPEL, "CT_PrincessCarryingAbility", t("carrying"), P_CARRYING_MGEF, SPELL_ABILITY,
             CONSTANT, SELF),
    ]
    control = script("CT_Control", [
        prop("ActorTypeNPC", ACTOR_TYPE_NPC), prop("CarriedAbility", CARRIED_SPEL),
        prop("CarryingAbility", CARRYING_SPEL), prop("HopOnPower", HOP_SPEL),
        prop("OffsetX", OFFSET_X), prop("OffsetY", OFFSET_Y), prop("OffsetZ", OFFSET_Z),
        prop("Rotation", ROTATION), prop("StyleMenu", STYLE_MENU), prop("Hotkey", HOTKEY),
        prop("PrincessCarriedAbility", P_CARRIED_SPEL), prop("PrincessCarryingAbility", P_CARRYING_SPEL),
        prop("PrincessOffsetX", P_OFFSET_X), prop("PrincessOffsetY", P_OFFSET_Y),
        prop("PrincessOffsetZ", P_OFFSET_Z), prop("PrincessRotation", P_ROTATION),
        prop("Passenger", QUEST, alias=1), prop("PlayerRef", PLAYER_REF),
    ])
    quest = record(b"QUST", QUEST, [
        (b"EDID", z("CT_Control")),
        (b"VMAD", quest_vmad([control], [(0, [script("CT_PlayerAlias")]), (1, [script("CT_PassengerAlias")])])),
        (b"DNAM", bytes.fromhex("1100 50ff 00000000 00000000")),   # start game enabled, as Carry Me
        (b"NEXT", b""), (b"ANAM", struct.pack("<I", 2)),
        (b"ALST", struct.pack("<I", 0)), (b"ALID", z("Player")), (b"FNAM", struct.pack("<I", 0)),
        (b"ALFR", struct.pack("<I", PLAYER_REF)), (b"VTCK", struct.pack("<I", 0)), (b"ALED", b""),
        (b"ALST", struct.pack("<I", 1)), (b"ALID", z("Passenger")), (b"FNAM", struct.pack("<I", 2)),  # optional
        (b"VTCK", struct.pack("<I", 0)), (b"ALED", b""),
    ])
    # Separate quest so the MCM stays optional: without MCM Helper its script just fails to bind.
    mcm = record(b"QUST", MCM_QUEST, [
        (b"EDID", z("CT_MCM")),
        (b"VMAD", quest_vmad([script("CT_MCM", [prop("Control", QUEST)])], [(0, [script("SKI_PlayerLoadGameAlias")])], MCM_QUEST)),
        (b"DNAM", bytes.fromhex("1100 50ff 00000000 00000000")),
        (b"NEXT", b""), (b"ANAM", struct.pack("<I", 1)),
        (b"ALST", struct.pack("<I", 0)), (b"ALID", z("Player")), (b"FNAM", struct.pack("<I", 0)),
        (b"ALFR", struct.pack("<I", PLAYER_REF)), (b"VTCK", struct.pack("<I", 0)), (b"ALED", b""),
    ])
    quests = [quest, mcm]
    menu = record(b"MESG", STYLE_MENU, [
        (b"EDID", z("CT_StyleMenu")), (b"DESC", z(t("menu"))),
        (b"INAM", b"\0" * 4), (b"DNAM", struct.pack("<I", 1)),       # flags: message box
        (b"ITXT", z(t("menu_back"))), (b"ITXT", z(t("menu_arms"))), (b"ITXT", z(t("menu_cancel"))),
    ])
    # Top groups in the game's own order (MESG comes after QUST).
    groups = (group(b"GLOB", globs) + group(b"MGEF", mgefs) + group(b"SPEL", spells) + group(b"QUST", quests)
              + group(b"MESG", [menu]))
    count = len(globs) + 1 + len(mgefs) + len(spells) + len(quests) + 5    # records + top groups
    return header(count, NEXT_OBJECT_ID,
                  "Carry Them: carry an NPC on your back. Uses Piggyback, Offset Movement Animation and OAR.",
                  ["Skyrim.esm"]) + groups


# --- Optional dialogue plugin -------------------------------------------------------------------
# "CarryThem - Dialogue.esp" (ESL, masters Skyrim.esm + CarryThem.esp): a top-level player line
# "Let me carry you." on any NPC, who answers "How?"; the player then picks "On my back.", "In my
# arms." or "Never mind.". The first two end the conversation and their end fragment (CT_TIF_Carry,
# Style property) calls CT_Control.CarryAs. Own records use index 02; CarryThem.esp's use 01.
DIALOGUE_PLUGIN = "CarryThem - Dialogue.esp"
D_OWN, D_MAIN = 0x02000000, 0x01000000
(D_QUEST, D_TOPIC, D_INFO, D_BRANCH, D_BACK_TOPIC, D_BACK_INFO, D_ARMS_TOPIC, D_ARMS_INFO,
 D_NEVERMIND_TOPIC, D_NEVERMIND_INFO) = range(D_OWN | 0x800, D_OWN | 0x80A)
D_NEXT_OBJECT_ID = 0x80A
GET_DEAD, HAS_SPELL, HAS_KEYWORD = 46, 264, 560      # condition function indices (CommonLibSSE TESCondition.h)
RUN_ON_SUBJECT, RUN_ON_REFERENCE = 0, 2
INFO_GOODBYE, INFO_FORCE_SUBTITLE = 0x1, 0x100


def prop_str(name, value):
    return wstr(name) + struct.pack("<BB", 2, 1) + wstr(value)          # type String, status Edited


def prop_int(name, value):
    return wstr(name) + struct.pack("<BBi", 3, 1, value)               # type Int, status Edited


def ctda(function, param, value, run_on=RUN_ON_SUBJECT, reference=0):
    """One condition, function(param) == value (operator == is 0 in the top 3 bits of the first byte)."""
    return (b"CTDA", struct.pack("<B3sfHHIIIIi", 0, b"\0" * 3, value, function, 0, param, 0, run_on, reference, -1))


def info_vmad(fragment_script, props):
    """VMAD of a dialogue line with one end fragment: the TIF script, then its fragment table."""
    return (scripts(script(fragment_script, props))
            + struct.pack("<BB", 2, 0x2) + wstr(fragment_script)               # flags: end fragment only
            + struct.pack("<B", 0) + wstr(fragment_script) + wstr("Fragment_0"))


def info(fid, prompt, reply, flags, before_reply=(), after_reply=(), vmad=None):
    """A player line (prompt) and the NPC's silent reply, shown as a subtitle."""
    trdt = struct.pack("<IIIB3sIB3s", 0, 50, 0, 1, b"\0" * 3, 0, 0, b"\0" * 3)  # neutral 50, response 1
    return record(b"INFO", fid, ([(b"VMAD", vmad)] if vmad else []) + [
        (b"ENAM", struct.pack("<HH", flags | INFO_FORCE_SUBTITLE, 0)),
        (b"CNAM", b"\0"),                                              # favor level: none
    ] + list(before_reply) + [
        (b"TRDT", trdt), (b"NAM1", z(reply)), (b"NAM2", z("")), (b"NAM3", z("")),
    ] + list(after_reply) + [(b"RNAM", z(prompt))])


def topic(fid, edid, text, line):
    """A Custom player topic of CT_CarryBranch, followed by its group of lines (group type 7)."""
    return record(b"DIAL", fid, [
        (b"EDID", z(edid)), (b"FULL", z(text)),
        (b"PNAM", struct.pack("<f", 50.0)), (b"BNAM", struct.pack("<I", D_BRANCH)),
        (b"QNAM", struct.pack("<I", D_QUEST)),
        (b"DATA", struct.pack("<BBH", 0, 0, 0)),                        # category Topic, subtype Custom
        (b"SNAM", b"CUST"), (b"TIFC", struct.pack("<I", 1)),
    ]) + group(struct.pack("<I", fid), [line], 7)


def build_dialogue():
    quest = record(b"QUST", D_QUEST, [
        (b"EDID", z("CT_DialogueQuest")),
        (b"DNAM", bytes.fromhex("1100 50ff 00000000 00000000")),   # start game enabled, as CT_Control
        (b"NEXT", b""), (b"ANAM", struct.pack("<I", 0)),
    ])
    ask = info(D_INFO, t("ask"), t("how"), 0,
               before_reply=[(b"TCLT", struct.pack("<I", t)) for t in (D_BACK_TOPIC, D_ARMS_TOPIC, D_NEVERMIND_TOPIC)],
               after_reply=[
                   ctda(HAS_KEYWORD, ACTOR_TYPE_NPC, 1.0),
                   ctda(GET_DEAD, 0, 0.0),
                   # Hidden while the player already carries someone (either carrying pose marker).
                   ctda(HAS_SPELL, D_MAIN | 0x806, 0.0, RUN_ON_REFERENCE, PLAYER_REF),
                   ctda(HAS_SPELL, D_MAIN | 0x811, 0.0, RUN_ON_REFERENCE, PLAYER_REF),
               ])

    def carry(fid, prompt, style):
        return info(fid, prompt, t("ok"), INFO_GOODBYE,
                    vmad=info_vmad("CT_TIF_Carry", [prop("Control", D_MAIN | 0x800), prop_int("Style", style)]))
    topics = [
        topic(D_TOPIC, "CT_CarryTopic", t("ask"), ask),
        topic(D_BACK_TOPIC, "CT_CarryBackTopic", t("back"), carry(D_BACK_INFO, t("back"), 0)),
        topic(D_ARMS_TOPIC, "CT_CarryArmsTopic", t("arms"), carry(D_ARMS_INFO, t("arms"), 1)),
        topic(D_NEVERMIND_TOPIC, "CT_CarryNevermindTopic", t("nevermind"),
              info(D_NEVERMIND_INFO, t("nevermind"), t("ok_nevermind"), INFO_GOODBYE)),
    ]
    branch = record(b"DLBR", D_BRANCH, [
        (b"EDID", z("CT_CarryBranch")), (b"QNAM", struct.pack("<I", D_QUEST)),
        (b"TNAM", struct.pack("<I", 0)),                                # category: Player
        (b"DNAM", struct.pack("<I", 1)),                                # flags: top-level
        (b"SNAM", struct.pack("<I", D_TOPIC)),
    ])
    # Top groups in the game's own order: DIAL (each topic followed by its lines), QUST, then DLBR.
    groups = group(b"DIAL", topics) + group(b"QUST", [quest]) + group(b"DLBR", [branch])
    count = 10 + 4 + 3                                                  # records + topics' groups + top groups
    seq = struct.pack("<I", D_QUEST)                                    # SEQ: the start-game-enabled quest
    return header(count, D_NEXT_OBJECT_ID, "Carry Them: optional dialogue line to pick someone up.",
                  ["Skyrim.esm", "CarryThem.esp"]) + groups, seq


# --- Optional SkyPrompt plugin ------------------------------------------------------------------
# "CarryThem - SkyPrompt.esp" (ESL, masters Skyrim.esm + CarryThem.esp): CT_SkyPrompt shows a hold
# prompt on the NPC in the crosshair. Same index layout as the dialogue plugin. No dialogue: no SEQ.
SKYPROMPT_PLUGIN = "CarryThem - SkyPrompt.esp"
S_QUEST, S_KEY, S_PAD_KEY = range(D_OWN | 0x800, D_OWN | 0x803)
S_NEXT_OBJECT_ID = 0x803


def build_skyprompt():
    globs = [glob(S_KEY, "CT_PromptKey", 34.0),                  # G
             glob(S_PAD_KEY, "CT_PromptGamepadKey", 278.0)]      # X / Square, as RSE
    control = script("CT_SkyPrompt", [
        prop("ActorTypeNPC", ACTOR_TYPE_NPC), prop("Control", D_MAIN | 0x800),
        prop("Enabled", D_MAIN | 0x818), prop("GamepadKey", S_PAD_KEY), prop("KeyboardKey", S_KEY),
        prop_str("CarryText", t("prompt_carry")), prop_str("DropText", t("prompt_drop")),
    ])
    quest = record(b"QUST", S_QUEST, [
        (b"EDID", z("CT_SkyPromptQuest")),
        (b"VMAD", quest_vmad([control], [(0, [script("CT_SkyPromptPlayer")])], S_QUEST)),
        (b"DNAM", bytes.fromhex("1100 50ff 00000000 00000000")),   # start game enabled, as CT_Control
        (b"NEXT", b""), (b"ANAM", struct.pack("<I", 1)),
        (b"ALST", struct.pack("<I", 0)), (b"ALID", z("Player")), (b"FNAM", struct.pack("<I", 0)),
        (b"ALFR", struct.pack("<I", PLAYER_REF)), (b"VTCK", struct.pack("<I", 0)), (b"ALED", b""),
    ])
    count = len(globs) + 1 + 2                                          # records + top groups
    return header(count, S_NEXT_OBJECT_ID, "Carry Them: optional SkyPrompt prompt to pick someone up.",
                  ["Skyrim.esm", "CarryThem.esp"]) + group(b"GLOB", globs) + group(b"QUST", [quest])


def check(data):
    """Walks the file back: every size field must land exactly on the next header."""
    def walk(o, end):
        n = 0
        while o < end:
            size = struct.unpack_from("<I", data, o + 4)[0]
            if data[o:o + 4] == b"GRUP":
                n += 1 + walk(o + 24, o + size)
                o += size
                continue
            p, stop = o + 24, o + 24 + size
            while p < stop:
                p += 6 + struct.unpack_from("<H", data, p + 4)[0]
            assert p == stop, f"subrecords overrun in {data[o:o + 4]} at {o:#x}"
            n, o = n + 1, stop
        assert o == end, "group size mismatch"
        return n
    tes4 = 24 + struct.unpack_from("<I", data, 4)[0]
    found = walk(tes4, len(data))
    assert found == struct.unpack_from("<I", data, 34)[0], "HEDR record count is wrong"


if __name__ == "__main__":
    LANG = sys.argv[2] if len(sys.argv) > 2 else "en"
    dialogue, seq = build_dialogue()
    outputs = ((PLUGIN, build()), (DIALOGUE_PLUGIN, dialogue), (os.path.join("SEQ", "CarryThem - Dialogue.seq"), seq),
               (SKYPROMPT_PLUGIN, build_skyprompt()))
    outputs += tuple((os.path.join("Interface", "Translations", f"CarryThem_{g}.txt"), translation_file())
                     for g in GAME_LANGUAGES)
    for name, data in outputs:
        if name.endswith(".esp"):
            check(data)
        path = os.path.join(sys.argv[1], name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        print("OK:", path, len(data), "bytes")
