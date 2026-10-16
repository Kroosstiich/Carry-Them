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
Usage: python build_plugin.py <output folder>
"""
import os, struct, sys

PLUGIN = "CarryThem.esp"
OWN = 0x01000000                     # one master (Skyrim.esm) -> our records use index 01
QUEST, HOP_MGEF, HOP_SPEL, CARRIED_MGEF, CARRIED_SPEL, CARRYING_MGEF, CARRYING_SPEL = range(OWN | 0x800, OWN | 0x807)
OFFSET_X, OFFSET_Y, OFFSET_Z, ROTATION, MCM_QUEST = range(OWN | 0x807, OWN | 0x80C)
NEXT_OBJECT_ID = 0x80C
OFFSET_DEFAULTS = (0.0, -35.0, -25.0)  # tuned in game (Carry Me's piggyback was 0, -30, 0)
ROTATION_DEFAULT = 10.0                # tuned in game: the pose faced slightly left
PLAYER_REF, ACTOR_TYPE_NPC, EQUIP_VOICE = 0x14, 0x13794, 0x25BEE
FLAG_ESL = 0x200


def z(s):
    return s.encode("cp1252") + b"\0"


def sub(sig, data):
    return sig + struct.pack("<H", len(data)) + data


def record(sig, fid, subs):
    body = b"".join(sub(s, d) for s, d in subs)
    return sig + struct.pack("<IIIIHH", len(body), 0, fid, 0, 44, 0) + body


def group(sig, records):
    body = b"".join(records)
    return b"GRUP" + struct.pack("<I", 24 + len(body)) + sig + struct.pack("<iHHI", 0, 0, 0, 0) + body


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
    mgefs = [
        mgef(HOP_MGEF, "CT_HopOnEffect", "Carry Them", FIRE_AND_FORGET, TARGET_ACTOR,
             scripts(script("CT_HopOnEffect", [prop("Control", QUEST)]))),
        mgef(CARRIED_MGEF, "CT_CarriedEffect", "Being Carried", CONSTANT, SELF),
        mgef(CARRYING_MGEF, "CT_CarryingEffect", "Carrying Someone", CONSTANT, SELF,
             desc="Your hands are busy holding someone on your back. Jump to set them down."),
    ]
    spells = [
        spel(HOP_SPEL, "CT_HopOnPower", "Carry Them", HOP_MGEF, SPELL_POWER_LESSER, FIRE_AND_FORGET,
             TARGET_ACTOR, "Carry someone on your back. Jump to set them down.", 5.0),
        spel(CARRIED_SPEL, "CT_CarriedAbility", "Being Carried", CARRIED_MGEF, SPELL_ABILITY, CONSTANT, SELF),
        spel(CARRYING_SPEL, "CT_CarryingAbility", "Carrying Someone", CARRYING_MGEF, SPELL_ABILITY, CONSTANT, SELF),
    ]
    control = script("CT_Control", [
        prop("ActorTypeNPC", ACTOR_TYPE_NPC), prop("CarriedAbility", CARRIED_SPEL),
        prop("CarryingAbility", CARRYING_SPEL), prop("HopOnPower", HOP_SPEL),
        prop("OffsetX", OFFSET_X), prop("OffsetY", OFFSET_Y), prop("OffsetZ", OFFSET_Z),
        prop("Rotation", ROTATION),
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
        (b"VMAD", quest_vmad([script("CT_MCM")], [(0, [script("SKI_PlayerLoadGameAlias")])], MCM_QUEST)),
        (b"DNAM", bytes.fromhex("1100 50ff 00000000 00000000")),
        (b"NEXT", b""), (b"ANAM", struct.pack("<I", 1)),
        (b"ALST", struct.pack("<I", 0)), (b"ALID", z("Player")), (b"FNAM", struct.pack("<I", 0)),
        (b"ALFR", struct.pack("<I", PLAYER_REF)), (b"VTCK", struct.pack("<I", 0)), (b"ALED", b""),
    ])
    quests = [quest, mcm]
    groups = group(b"GLOB", globs) + group(b"MGEF", mgefs) + group(b"SPEL", spells) + group(b"QUST", quests)
    count = len(globs) + len(mgefs) + len(spells) + len(quests) + 4    # records + top groups
    head = b"".join(sub(s, d) for s, d in [
        (b"HEDR", struct.pack("<fII", 1.71, count, NEXT_OBJECT_ID)), (b"CNAM", z("Kroosstii")),
        (b"SNAM", z("Carry Them: carry an NPC on your back. Uses Piggyback, Offset Movement Animation and OAR.")),
        (b"MAST", z("Skyrim.esm")), (b"DATA", b"\0" * 8),
    ])
    return b"TES4" + struct.pack("<IIIIHH", len(head), FLAG_ESL, 0, 0, 44, 0) + head + groups


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
    out = build()
    check(out)
    os.makedirs(sys.argv[1], exist_ok=True)
    with open(os.path.join(sys.argv[1], PLUGIN), "wb") as f:
        f.write(out)
    print("OK:", os.path.join(sys.argv[1], PLUGIN), len(out), "bytes")
