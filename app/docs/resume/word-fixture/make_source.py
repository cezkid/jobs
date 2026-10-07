"""Fake-data resume source for Word to re-save + export. Every name, place and number is made up.

uv run --no-project --with python-docx python make_source.py <dir>/source.docx, then
osascript resave.applescript <dir>, then set docProps/core.xml creator + lastModifiedBy to
"CEZ Job Finder test" (Word stamps the computer's account name). python-docx only builds the input;
the committed files are Word's own save. word-resume-clipped = the same w/ the text box 640080 EMU
tall (clips its 3rd line on the page). app/docs/resume/resume-file.md #Word-made test files."""
import sys
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.shared import Pt

doc = Document()
st = doc.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(10.5)
head = doc.sections[0].header
head.paragraphs[0].text = "Alex Rivera"
head.add_paragraph("Riverton, OH | alex.rivera@example.com | (555) 010-0199 | linkedin.com/in/alex-rivera-example")

def heading(text):
    p = doc.add_paragraph(); r = p.add_run(text); r.bold = True

def bullet(text, level=1):
    doc.add_paragraph(text, style="List Bullet" if level == 1 else "List Bullet 2")

heading("PROFESSIONAL SUMMARY")
doc.add_paragraph("Operations lead for regional freight and warehouse teams, 14 years across receiving, inventory and dispatch.")
heading("PROFESSIONAL EXPERIENCE")
jobs = [
    ("Northwind Logistics", "Columbus, OH", "Operations Manager", "10/2024 - Present",
     ["Cut dock-to-stock time 18% by redesigning the receiving flow", ("Trained 12 new leads on the warehouse system", 2),
      ("Ran weekly safety reviews across 3 shifts", 2), "Lowered overtime spend 9% in the first year"]),
    ("Contoso Freight", "Dayton, OH", "Shift Supervisor", "03/2019 - 09/2024",
     ["Scheduled 40 drivers across two depots", "Kept on-time dispatch at 96% through two peak seasons"]),
    ("Fabrikam Supply", "Akron, OH", "Inventory Clerk", "07/2007 - 06/2013",
     ["Counted cycle stock for 2,000 bins each quarter"]),
]
for company, place, title, dates, bullets in jobs:
    t = doc.add_table(rows=2, cols=2); t.alignment = WD_TABLE_ALIGNMENT.LEFT
    t.cell(0, 0).text, t.cell(0, 1).text = company, place
    t.cell(1, 0).text, t.cell(1, 1).text = title, dates
    for b in bullets:
        bullet(*b) if isinstance(b, tuple) else bullet(b)
heading("SKILLS")
doc.add_paragraph("Warehouse Systems - SAP EWM, Manhattan WMS")
doc.add_paragraph("Lean Practice - 5S, Kaizen, Value Stream Mapping")
heading("EDUCATION")
doc.add_paragraph("Ohio State University")
doc.add_paragraph("B.S. Industrial Engineering, 05/2007")
# a text box beside the certifications, as resume templates use them
box = doc.add_paragraph()
box._p.append(parse_xml(
 '<w:r xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
 'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
 'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
 'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">'
 '<mc:AlternateContent><mc:Choice Requires="wps"><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
 '<wp:extent cx="4572000" cy="914400"/><wp:docPr id="7" name="Certifications box"/>'
 '<a:graphic><a:graphicData uri="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">'
 '<wps:wsp><wps:cNvSpPr txBox="1"/><wps:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="4572000" cy="914400"/></a:xfrm>'
 '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:ln><a:noFill/></a:ln></wps:spPr>'
 '<wps:txbx><w:txbxContent><w:p><w:r><w:rPr><w:b/></w:rPr><w:t>CERTIFICATIONS</w:t></w:r></w:p>'
 '<w:p><w:r><w:t>Lean Six Sigma Green Belt, ASQ, 03/2019</w:t></w:r></w:p>'
 '<w:p><w:r><w:t>OSHA 30-Hour General Industry, 2021</w:t></w:r></w:p></w:txbxContent></wps:txbx>'
 '<wps:bodyPr rot="0" vert="horz" wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" anchor="t"/></wps:wsp>'
 '</a:graphicData></a:graphic></wp:inline></w:drawing></mc:Choice></mc:AlternateContent></w:r>'))
doc.save(sys.argv[1])
