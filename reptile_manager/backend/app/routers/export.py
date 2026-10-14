"""
PDF export: inventory list and Herkunftsnachweis.
Supports both Bearer token (header) and ?token= query param for browser downloads.
"""
import io
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                 Paragraph, Spacer, HRFlowable, KeepTogether)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from .. import models, auth
from ..database import get_db
from ..access import scope_animals

router = APIRouter()

W, H = A4
GREY   = colors.HexColor("#555555")
LGREY  = colors.HexColor("#eeeeee")
BLACK  = colors.black
BORDER = colors.HexColor("#cccccc")


def _get_user_flex(
    db: Session = Depends(get_db),
    token: Optional[str] = Query(None),
    current_user: Optional[models.User] = Depends(auth.get_current_user_optional),
):
    """Accept auth either via Authorization header or ?token= query param."""
    if current_user:
        return current_user
    if token:
        user = auth.get_user_from_token(token, db)
        if user:
            return user
    raise HTTPException(status_code=401, detail="Not authenticated")

import io, csv

# ── Inventory CSV export ──────────────────────────────────────────────────────

@router.get("/inventory")
def export_inventory(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_get_user_flex),
    token: Optional[str] = Query(None),
):
    animals = (scope_animals(db.query(models.Animal), current_user)
               .filter(models.Animal.status == "active")
               .order_by(models.Animal.species, models.Animal.name)
               .all())

    out = io.StringIO()
    w = csv.writer(out, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    w.writerow(["Tier-Nr.", "Name", "Wissenschaftlicher Name", "Trivialname",
                "Geschlecht", "Morph", "Geburtsdatum", "Gewicht (g)", "Länge (cm)",
                "Substrat", "Terrarium", "Temp. Tag °C", "Temp. Nacht °C",
                "Luftfeuchtigkeit %", "Status"])
    for a in animals:
        w.writerow([
            a.tracking_id or a.id,
            a.name or "",
            a.species or "",
            a.common_name or "",
            _sex_notation(a.sex),
            a.morph or "",
            _fmt_date(a.date_of_birth),
            a.weight_g or "",
            a.length_cm or "",
            a.substrate or "",
            a.terrarium_size or "",
            a.temp_day_c or "",
            a.temp_night_c or "",
            f"{a.humidity_min or ''}–{a.humidity_max or ''}" if (a.humidity_min or a.humidity_max) else "",
            a.status or "active",
        ])

    content = "\ufeff" + out.getvalue()   # UTF-8 BOM — Excel öffnet Umlaute korrekt
    fname = f"bestandsliste_{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(
        content=content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )

def _cb(checked, text_str, styles):
    """Render a checkbox row using a bordered table cell — works with standard fonts."""
    mark = "X" if checked else " "
    t = Table(
        [[mark, Paragraph(text_str, styles["body"])]],
        colWidths=[6*mm, 155*mm],
    )
    t.setStyle(TableStyle([
        ("BOX",           (0, 0), (0, 0), 0.6, BLACK),
        ("FONTNAME",      (0, 0), (0, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (0, 0), 9),
        ("ALIGN",         (0, 0), (0, 0), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("LEFTPADDING",   (0, 0), (0, 0), 0),
        ("RIGHTPADDING",  (0, 0), (0, 0), 2),
        ("LEFTPADDING",   (1, 0), (1, 0), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t
    return {"male": "Männlich", "female": "Weiblich", "unknown": "Unbekannt"}.get(
        sex.value if hasattr(sex, "value") else str(sex), "?"
    )

def _sex_notation(sex):
    """Reptile/spider standard notation: male.female.unknown"""
    v = sex.value if hasattr(sex, "value") else str(sex)
    if v == "male":   return "1.0.0"
    if v == "female": return "0.1.0"
    return "0.0.1"

def _fmt_date(d):
    return d.strftime("%d.%m.%Y") if d else "—"

def _styles():
    base = getSampleStyleSheet()
    return {
        "h1":    ParagraphStyle("h1",    fontName="Helvetica-Bold",  fontSize=16, alignment=TA_CENTER, spaceAfter=2*mm),
        "h2":    ParagraphStyle("h2",    fontName="Helvetica-Bold",  fontSize=11, spaceAfter=2*mm),
        "small": ParagraphStyle("small", fontName="Helvetica",       fontSize=8,  textColor=GREY),
        "body":  ParagraphStyle("body",  fontName="Helvetica",       fontSize=9,  leading=13, spaceAfter=2*mm),
        "bold":  ParagraphStyle("bold",  fontName="Helvetica-Bold",  fontSize=9,  spaceAfter=1*mm),
        "legal": ParagraphStyle("legal", fontName="Helvetica-Oblique",fontSize=8, textColor=GREY, spaceAfter=3*mm),
        "center":ParagraphStyle("center",fontName="Helvetica",       fontSize=9,  alignment=TA_CENTER),
    }

def _pdf_response(buf, filename):
    buf.seek(0)
    return Response(
        content=buf.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Herkunftsnachweis ─────────────────────────────────────────────────────────

class HerkunftsnachweisRequest(BaseModel):
    animal_ids: List[int]
    buyer_name:     str = ""
    buyer_street:   str = ""
    buyer_zip_city: str = ""
    buyer_phone:    str = ""
    origin_type:    str = "nachzucht"   # bestand | nachzucht | einfuhr | sonstiges
    cites_nr:       str = ""
    einfuhr_nr:     str = ""
    sonstiges_text: str = ""
    ort_datum:      str = ""
    blanko:         bool = False


@router.post("/herkunftsnachweis")
def export_herkunftsnachweis(
    req: HerkunftsnachweisRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(_get_user_flex),
):
    cfg  = db.query(models.HAConfig).first()
    tiere = (scope_animals(db.query(models.Animal), current_user)
              .filter(models.Animal.id.in_(req.animal_ids))
              .all())
    id_map = {a.id: a for a in tiere}
    tiere_ordered = [id_map[i] for i in req.animal_ids if i in id_map]

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    s = _styles()
    els = []

    # ── Title ──
    els.append(Paragraph("HERKUNFTSNACHWEIS", s["h1"]))
    els.append(Paragraph(
        "Herkunftsnachweis zum Nachweis der Legalität nach § 46 BNatSchG",
        ParagraphStyle("legal2", fontName="Helvetica-Bold", fontSize=9,
                       alignment=TA_CENTER, textColor=GREY, spaceAfter=5*mm)
    ))

    # ── Seller / Buyer two-column table ──
    seller_name  = (cfg.breeder_name     if cfg else "") or ""
    seller_str   = (cfg.breeder_street   if cfg else "") or ""
    seller_plz   = (cfg.breeder_zip_city if cfg else "") or ""
    seller_tel   = (cfg.breeder_phone    if cfg else "") or ""

    def info_cell(label, name, street, plz, phone):
        lines = (
            f"<b>{label}</b><br/>"
            f"Name: {name or '___________________________'}<br/>"
            f"Straße: {street or '___________________________'}<br/>"
            f"PLZ/Ort: {plz or '___________________________'}<br/>"
            f"Telefon: {phone or '___________________________'}"
        )
        return Paragraph(lines, ParagraphStyle("cell", fontName="Helvetica",
                                                fontSize=9, leading=14))

    contact_table = Table(
        [[info_cell("Verkäufer / Züchter", seller_name, seller_str, seller_plz, seller_tel),
          info_cell("Käufer / Erwerber", req.buyer_name, req.buyer_street, req.buyer_zip_city, req.buyer_phone)]],
        colWidths=[83*mm, 83*mm],
    )
    contact_table.setStyle(TableStyle([
        ("BOX",        (0,0), (-1,-1), 0.5, BORDER),
        ("INNERGRID",  (0,0), (-1,-1), 0.5, BORDER),
        ("TOPPADDING", (0,0), (-1,-1), 3*mm),
        ("BOTTOMPADDING",(0,0),(-1,-1),3*mm),
        ("LEFTPADDING",(0,0), (-1,-1), 3*mm),
    ]))
    els.append(contact_table)
    els.append(Spacer(1, 5*mm))

    # ── Declaration ──
    els.append(Paragraph(
        "Ich versichere, dass folgende, von mir abgegebenen Tiere:",
        ParagraphStyle("decl", fontName="Helvetica-Bold", fontSize=10, spaceAfter=3*mm)
    ))

    # ── Animal table ──
    ah = ["Anz.", "Gesch.", "Wissenschaftlicher Name", "Tier-Nr.", "Herkunft von"]
    animal_rows = [ah]
    for a in tiere_ordered:
        mother = db.query(models.Animal).filter(models.Animal.id == a.mother_id).first() if a.mother_id else None
        father = db.query(models.Animal).filter(models.Animal.id == a.father_id).first() if a.father_id else None
        eltern = []
        if mother: eltern.append(f"Mutter: {mother.name} #{mother.tracking_id or mother.id}")
        if father: eltern.append(f"Vater: {father.name} #{father.tracking_id or father.id}")
        animal_rows.append([
            "1",
            _sex_notation(a.sex),
            a.species or "—",
            str(a.tracking_id) if a.tracking_id else str(a.id),
            ", ".join(eltern) if eltern else "—",
        ])

    at = Table(animal_rows, colWidths=[10*mm, 18*mm, 65*mm, 22*mm, 51*mm], repeatRows=1)
    at.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  colors.HexColor("#1e2433")),
        ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),  [colors.white, LGREY]),
        ("GRID",          (0,0), (-1,-1), 0.3, BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 2*mm),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2*mm),
        ("LEFTPADDING",   (0,0), (-1,-1), 2*mm),
    ]))
    els.append(at)
    els.append(Spacer(1, 5*mm))

    # ── Checkboxes ──
    els.append(Spacer(1, 2*mm))
    els.append(_cb(req.origin_type == "bestand",   "aus meinem legalen Bestand stammen", s))
    els.append(Spacer(1, 1*mm))
    els.append(_cb(req.origin_type == "nachzucht", "aus meiner legalen Nachzucht stammen", s))
    els.append(Spacer(1, 1*mm))

    cites_line = "aus genehmigter Einfuhr stammen"
    if req.origin_type == "einfuhr" and (req.cites_nr or req.einfuhr_nr):
        cites_line += f"  (Cites-Nr: {req.cites_nr or '—'}   Einfuhr-Nr: {req.einfuhr_nr or '—'})"
    els.append(_cb(req.origin_type == "einfuhr", cites_line, s))
    els.append(Spacer(1, 1*mm))

    sonst = "Sonstiges"
    if req.origin_type == "sonstiges" and req.sonstiges_text:
        sonst += f": {req.sonstiges_text}"
    els.append(_cb(req.origin_type == "sonstiges", sonst, s))

    els.append(Spacer(1, 10*mm))

    # ── Ort / Datum (pre-filled) ──
    ort_name  = req.ort_datum.strip() if req.ort_datum else "_______________"
    datum_str = datetime.now().strftime("%d.%m.%Y")
    ort_line  = f"{ort_name}, den {datum_str}"

    ort_table = Table(
        [[Paragraph(ort_line, s["body"]), Paragraph("", s["body"])]],
        colWidths=[83*mm, 83*mm],
    )
    ort_table.setStyle(TableStyle([
        ("TOPPADDING",    (0,0),(-1,-1), 1),
        ("BOTTOMPADDING", (0,0),(-1,-1), 1),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
    ]))
    els.append(ort_table)

    # ── 30 mm space for actual signature ──
    els.append(Spacer(1, 30*mm))

    # ── Signature lines ──
    sig_line_table = Table(
        [
            [HRFlowable(width=80*mm, thickness=0.6, color=BLACK),
             HRFlowable(width=80*mm, thickness=0.6, color=BLACK)],
            [Paragraph("Unterschrift <b>Verkäufer / Züchter</b>", s["small"]),
             Paragraph("Unterschrift <b>Käufer / Erwerber</b>",   s["small"])],
        ],
        colWidths=[83*mm, 83*mm],
        rowHeights=[2*mm, 5*mm],
    )
    sig_line_table.setStyle(TableStyle([
        ("TOPPADDING",    (0,0),(-1,-1), 0),
        ("BOTTOMPADDING", (0,0),(-1,-1), 1),
        ("LEFTPADDING",   (0,0),(-1,-1), 0),
    ]))
    els.append(sig_line_table)
    els.append(Spacer(1, 5*mm))
    els.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    els.append(Spacer(1, 2*mm))
    els.append(Paragraph(
        f"Herkunftsnachweis zum Nachweis der Legalität nach § 46 BNatSchG &nbsp;|&nbsp; "
        f"Erstellt mit Reptile Manager am {datetime.now().strftime('%d.%m.%Y')} &nbsp;|&nbsp; "
        f"github.com/demrios-de/reptile-manager",
        s["legal"]
    ))

    doc.build(els)
    fname = f"herkunftsnachweis_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return _pdf_response(buf, fname)
