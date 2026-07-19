#!/usr/bin/env python3
"""Append three reflective AI-collaboration slides to the existing deck.

This avoids external PowerPoint libraries by editing the OpenXML package
directly. It adds slide XML, presentation relationships, slide IDs and content
type overrides while preserving the existing 22-slide deck.
"""

from __future__ import annotations

import copy
import html
import shutil
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


PPTX = Path(
    "/Users/jbb/Dropbox/GIVE/paper-2022-scc-give-zenodo/"
    "wildfire_extension/slides/wildfire_give_ai_bootcamp_deck.pptx"
)
BACKUP = PPTX.with_name("wildfire_give_ai_bootcamp_deck_22slide_backup.pptx")

P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"

ET.register_namespace("p", P)
ET.register_namespace("a", A)
ET.register_namespace("r", R)

EMU = 9525

C = {
    "paper": "F7F1E8",
    "white": "FFFDFC",
    "ink": "182321",
    "slate": "59635E",
    "line": "D7CDBF",
    "fire": "C84E2D",
    "spruce": "1F6B5B",
    "gold": "D6A13C",
    "pale_fire": "F4D5CA",
    "pale_spruce": "D7E9E2",
    "pale_gold": "F4E8C6",
    "dark_panel": "213330",
    "dark_panel_2": "263B37",
}


def emu(v: float) -> str:
    return str(int(round(v * EMU)))


def esc(text: str) -> str:
    return html.escape(text, quote=False)


class SlideBuilder:
    def __init__(self, number: int, dark: bool = False):
        self.number = number
        self.dark = dark
        self.next_id = 1
        self.parts: list[str] = []
        self.rect(0, 0, 1280, 720, C["ink"] if dark else C["paper"], "000000", 0)

    def _id(self) -> int:
        value = self.next_id
        self.next_id += 1
        return value

    def rect(self, x, y, w, h, fill, stroke=None, width=1, alpha=None):
        sid = self._id()
        stroke = stroke if stroke is not None else fill
        fill_xml = (
            f'<a:srgbClr val="{fill}"><a:alpha val="{alpha}"/></a:srgbClr>'
            if alpha is not None
            else f'<a:srgbClr val="{fill}"/>'
        )
        line_xml = (
            f'<a:ln w="{int(width * EMU)}"><a:solidFill><a:srgbClr val="{stroke}"/></a:solidFill>'
            '<a:prstDash val="solid"/></a:ln>'
            if width
            else '<a:ln w="0"><a:solidFill><a:srgbClr val="000000"><a:alpha val="0"/></a:srgbClr></a:solidFill></a:ln>'
        )
        self.parts.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name=""/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:solidFill>{fill_xml}</a:solidFill>{line_xml}</p:spPr></p:sp>'
        )

    def text(self, text, x, y, w, h, size=18, color=None, bold=False, font="Aptos", align="l", valign="t"):
        sid = self._id()
        color = color or (C["white"] if self.dark else C["ink"])
        bold_xml = ' b="1"' if bold else ' b="0"'
        paras = []
        for line in text.split("\n"):
            paras.append(
                f'<a:p><a:pPr algn="{align}"><a:defRPr sz="{int(size * 75)}"{bold_xml}>'
                f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
                f'<a:latin typeface="{font}"/><a:ea typeface="{font}"/><a:cs typeface="{font}"/>'
                f'</a:defRPr></a:pPr><a:r><a:rPr sz="{int(size * 75)}"{bold_xml}>'
                f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
                f'<a:latin typeface="{font}"/><a:ea typeface="{font}"/><a:cs typeface="{font}"/>'
                f'</a:rPr><a:t>{esc(line)}</a:t></a:r></a:p>'
            )
        self.parts.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name=""/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
            '<a:solidFill><a:srgbClr val="000000"><a:alpha val="0"/></a:srgbClr></a:solidFill>'
            '<a:ln w="0"><a:solidFill><a:srgbClr val="000000"><a:alpha val="0"/></a:srgbClr></a:solidFill></a:ln>'
            f'</p:spPr><p:txBody><a:bodyPr lIns="0" tIns="0" rIns="0" bIns="0" anchor="{valign}"/>'
            f'<a:lstStyle/>{"".join(paras)}</p:txBody></p:sp>'
        )

    def kicker(self, label):
        self.rect(48, 42, 38, 3, C["gold"] if self.dark else C["fire"], width=0)
        self.text(label.upper(), 98, 30, 420, 28, 12, C["pale_gold"] if self.dark else C["fire"], True, "Aptos")

    def title(self, text, y=82, size=42, h=112):
        self.text(text, 48, y, 1060, h, size, C["white"] if self.dark else C["ink"], True, "Aptos Display")

    def footer(self, source):
        self.text(source, 48, 684, 980, 22, 11, C["slate"], False, "Aptos")
        self.text(str(self.number).zfill(2), 1180, 684, 52, 22, 11, C["slate"], False, "Aptos", "r")

    def build(self):
        sp_tree = (
            '<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            '<p:grpSpPr><a:xfrm/></p:grpSpPr>'
            + "".join(self.parts)
            + "</p:spTree>"
        )
        return (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
            'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            f"<p:cSld>{sp_tree}</p:cSld></p:sld>"
        ).encode("utf-8")


def add_panel(slide, x, y, w, h, head, body, fill, stroke, head_color=None):
    slide.rect(x, y, w, h, fill, stroke, 1)
    slide.text(head, x + 22, y + 22, w - 44, 28, 19, head_color or C["ink"], True, "Aptos")
    slide.text(body, x + 22, y + 66, w - 44, h - 80, 15, C["slate"], False, "Aptos")


def slide_23():
    s = SlideBuilder(23)
    s.kicker("epistemic checks")
    s.title("How I judged whether the work was on solid ground.", h=96)
    cards = [
        ("Code over vibes", "I traced where CO2 enters GIVE, how FaIR receives it, and whether a warming-to-fire-to-CO2 loop exists."),
        ("Unit discipline", "I checked CO2 vs carbon, annual flows vs atmospheric stocks, and event-scale anchors such as Canada 2023."),
        ("Mechanism tests", "We used one-draw checks, a 1000% stress case, sectoral marginal damages and temperature-path diagnostics."),
        ("Literature triangulation", "I separated smoke mortality, gross fire emissions, net persistence and double-counting risk."),
    ]
    for i, (h, b) in enumerate(cards):
        x = 70 + (i % 2) * 555
        y = 210 + (i // 2) * 155
        add_panel(s, x, y, 490, 122, h, b, C["white"], C["line"], C["spruce"] if i != 2 else C["fire"])
    s.rect(150, 548, 900, 64, C["pale_gold"], C["gold"], 1)
    s.text(
        "Correct means a defensible conditional experiment, not proof that wildfire carbon is absent from every baseline pathway.",
        178, 566, 845, 28, 19, C["ink"], True, "Aptos", "ctr"
    )
    s.footer("Epistemic slide added after the 22-slide deck: methods for deciding whether the extension was justified.")
    return s.build()


def slide_24():
    s = SlideBuilder(24)
    s.kicker("roles and deference")
    s.title("This was a team process, but not a symmetric one.", h=96)
    add_panel(
        s, 70, 195, 335, 300, "Your role",
        "You set the hypothesis, challenged the scale, rejected weak figures, forced diagnostics and decided what mattered scientifically.",
        C["white"], C["line"], C["fire"],
    )
    add_panel(
        s, 435, 195, 335, 300, "My role",
        "I acted as research programmer, model auditor, literature scout and skeptical calculator: fast execution plus an evidence ledger.",
        C["pale_spruce"], C["spruce"], C["spruce"],
    )
    add_panel(
        s, 800, 195, 335, 300, "Where I deferred",
        "I ran experiments you asked for, including high-end stress tests, but labeled them as diagnostics when the accounting was not defensible.",
        C["white"], C["line"], C["gold"],
    )
    s.rect(132, 548, 945, 74, C["pale_fire"], C["fire"], 1)
    s.text(
        "I should not knowingly take a wrong path. If a run is useful but scientifically dubious, my job is to name it as a stress test, not launder it into a result.",
        162, 565, 885, 38, 18, C["ink"], True, "Aptos", "ctr",
    )
    s.footer("Role framing: PI/domain judgment from the human researcher; audit, implementation and challenge from the AI collaborator.")
    return s.build()


def slide_25():
    s = SlideBuilder(25, dark=True)
    s.kicker("what researchers miss")
    s.title("The best next questions are about boundaries, not just bigger runs.", size=43, h=112)
    questions = [
        ("Accounting", "What share of projected fire carbon is already embedded in AFOLU, LULUCF or aggregate scenario expectations?"),
        ("Physics", "What is net persistent CO2 after regrowth, combustion completeness and biome-specific recovery times?"),
        ("Data", "Can gridded fire-carbon projections replace hand-coded country source proxies?"),
        ("Damages", "Should smoke mortality and non-CO2 fire forcing be modeled as separate SCC channels?"),
        ("Uncertainty", "Can we sample uncertainty over model structure, not only over parameters?"),
    ]
    y = 205
    for i, (h, b) in enumerate(questions):
        fill = C["dark_panel"] if i % 2 == 0 else C["dark_panel_2"]
        s.rect(82, y, 1030, 60, fill, "41524C", 1)
        s.text(h, 112, y + 17, 190, 22, 17, C["pale_gold"], True, "Aptos")
        s.text(b, 335, y + 15, 710, 28, 16, "E9EFEA", False, "Aptos")
        y += 72
    s.text(
        "Team description: you are in charge of the research aims and norms; I expand the search space, execute carefully and surface objections you may not yet know to ask.",
        120, 598, 1000, 42, 21, C["white"], True, "Aptos", "ctr",
    )
    s.footer("Reflective close: the AI should make hidden uncertainty visible, not merely comply.")
    return s.build()


NEW_SLIDES = {
    23: slide_23(),
    24: slide_24(),
    25: slide_25(),
}


def rels_for_new_slide() -> bytes:
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" '
        'Target="/ppt/slideLayouts/slideLayout2.xml" Id="rId1" />'
        "</Relationships>"
    ).encode("utf-8")


def main() -> None:
    if not BACKUP.exists():
        shutil.copy2(PPTX, BACKUP)

    with zipfile.ZipFile(PPTX, "r") as zin:
        presentation = ET.fromstring(zin.read("ppt/presentation.xml"))
        rels = ET.fromstring(zin.read("ppt/_rels/presentation.xml.rels"))
        content_types = ET.fromstring(zin.read("[Content_Types].xml"))

        sld_id_lst = presentation.find(f"{{{P}}}sldIdLst")
        assert sld_id_lst is not None
        existing_ids = [int(el.attrib["id"]) for el in sld_id_lst.findall(f"{{{P}}}sldId")]
        next_id = max(existing_ids) + 1

        existing_rel_ids = {el.attrib["Id"] for el in rels.findall(f"{{{REL}}}Relationship")}
        existing_overrides = {
            el.attrib["PartName"] for el in content_types.findall(f"{{{CT}}}Override")
        }

        for slide_num in NEW_SLIDES:
            rid = f"Rreflective{slide_num}"
            while rid in existing_rel_ids:
                rid += "x"
            ET.SubElement(sld_id_lst, f"{{{P}}}sldId", {"id": str(next_id), f"{{{R}}}id": rid})
            next_id += 1
            ET.SubElement(
                rels,
                f"{{{REL}}}Relationship",
                {
                    "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide",
                    "Target": f"/ppt/slides/slide{slide_num}.xml",
                    "Id": rid,
                },
            )
            part_name = f"/ppt/slides/slide{slide_num}.xml"
            if part_name not in existing_overrides:
                ET.SubElement(
                    content_types,
                    f"{{{CT}}}Override",
                    {
                        "PartName": part_name,
                        "ContentType": "application/vnd.openxmlformats-officedocument.presentationml.slide+xml",
                    },
                )

        replacements = {
            "ppt/presentation.xml": ET.tostring(presentation, encoding="utf-8", xml_declaration=True),
            "ppt/_rels/presentation.xml.rels": ET.tostring(rels, encoding="utf-8", xml_declaration=True),
            "[Content_Types].xml": ET.tostring(content_types, encoding="utf-8", xml_declaration=True),
        }

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as tmp:
            tmp_path = Path(tmp.name)

        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zout:
            written = set()
            for item in zin.infolist():
                if item.filename in replacements:
                    zout.writestr(item, replacements[item.filename])
                    written.add(item.filename)
                elif item.filename not in written:
                    zout.writestr(item, zin.read(item.filename))
                    written.add(item.filename)
            for slide_num, slide_xml in NEW_SLIDES.items():
                zout.writestr(f"ppt/slides/slide{slide_num}.xml", slide_xml)
                zout.writestr(f"ppt/slides/_rels/slide{slide_num}.xml.rels", rels_for_new_slide())

    shutil.move(str(tmp_path), PPTX)
    print(f"Updated {PPTX} with slides 23-25.")
    print(f"Backup preserved at {BACKUP}.")


if __name__ == "__main__":
    main()
