import shutil
import subprocess
import sys
import zipfile

import pytest

from resume import word


@pytest.fixture
def no_textutil(monkeypatch):
    """Windows, or a Mac without textutil: .doc / .rtf / .odt get the save-as step."""
    monkeypatch.setattr(word.shutil, "which", lambda name: None)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
STRICT = "http://purl.oclc.org/ooxml/wordprocessingml/main"
MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"


def p(*runs: str) -> str:
    return "<w:p>" + "".join(runs) + "</w:p>"


def r(text: str, props: str = "") -> str:
    return f'<w:r>{f"<w:rPr>{props}</w:rPr>" if props else ""}<w:t xml:space="preserve">{text}</w:t></w:r>'


def part(body: str, root: str = "document", ns: str = W) -> str:
    inner = f"<w:body>{body}</w:body>" if root == "document" else body
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:{root} xmlns:w="{ns}" xmlns:mc="{MC}">{inner}</w:{root}>'


def docx(tmp_path, body: str, headers=(), footers=(), ns: str = W, name: str = "resume.docx"):
    path = tmp_path / name
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", part(body, ns=ns))
        for i, h in enumerate(headers, 1):
            z.writestr(f"word/header{i}.xml", part(h, "hdr", ns))
        for i, f in enumerate(footers, 1):
            z.writestr(f"word/footer{i}.xml", part(f, "ftr", ns))
    return path


def test_header_contact_comes_first_once_and_footer_last(tmp_path):
    contact = p(r("Alex Rivera")) + p(r("Riverton, OH | alex.rivera@example.com"))
    path = docx(tmp_path, p(r("PROFESSIONAL EXPERIENCE")), headers=[contact, contact],
                footers=[p(r("References on request"))])
    assert word.extract(path).splitlines() == [
        "Alex Rivera", "Riverton, OH | alex.rivera@example.com", "PROFESSIONAL EXPERIENCE", "References on request"]


def test_runs_join_tabs_and_breaks_split(tmp_path):
    body = p(r("Northwind "), r("Logistics"), "<w:r><w:tab/></w:r>", r("10/24 - Present")) + \
        p(r("Line one"), "<w:r><w:br/></w:r>", r("Line two"))
    assert word.extract(docx(tmp_path, body)).splitlines() == [
        "Northwind Logistics\t10/24 - Present", "Line one", "Line two"]


def test_table_layout_cells_read_in_order(tmp_path):
    body = "<w:tbl><w:tr><w:tc>" + p(r("Contoso Freight")) + "</w:tc><w:tc>" + p(r("03/2019 - 09/2024")) + \
        "</w:tc></w:tr></w:tbl>"
    assert word.extract(docx(tmp_path, body)).splitlines() == ["Contoso Freight", "03/2019 - 09/2024"]


def test_text_box_read_once_not_twice(tmp_path):
    box = p(r("Lean Six Sigma Green Belt"))
    body = p(f"<w:r><mc:AlternateContent><mc:Choice><w:txbxContent>{box}</w:txbxContent></mc:Choice>"
             f"<mc:Fallback><w:txbxContent>{box}</w:txbxContent></mc:Fallback></mc:AlternateContent></w:r>")
    assert word.extract(docx(tmp_path, body)).count("Lean Six Sigma") == 1


def test_what_word_does_not_show_is_left_out(tmp_path):
    body = p(r("Scheduled 40 drivers"), "<w:del><w:r><w:delText> and 9 trucks</w:delText></w:r></w:del>",
             "<w:ins>" + r(" across two depots") + "</w:ins>") + \
        p(r("Kubernetes Python Java", "<w:vanish/>"), r("Visible line")) + \
        p(r("Shown", '<w:vanish w:val="false"/>')) + \
        p('<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText> HYPERLINK "x" </w:instrText></w:r>',
          r("linkedin.com/in/alex"))
    assert word.extract(docx(tmp_path, body)).splitlines() == [
        "Scheduled 40 drivers across two depots", "Visible line", "Shown", "linkedin.com/in/alex"]


def test_symbol_bullet_and_hyphens(tmp_path):
    body = p('<w:r><w:sym w:font="Symbol" w:char="F0B7"/></w:r>', r(" Trained 12 leads")) + \
        p(r("cross"), "<w:r><w:noBreakHyphen/></w:r>", r("functional pro"), "<w:r><w:softHyphen/></w:r>", r("cess"))
    assert word.extract(docx(tmp_path, body)).splitlines() == [" Trained 12 leads", "cross-functional process"]


def test_content_controls_read(tmp_path):
    body = "<w:sdt><w:sdtPr/><w:sdtContent>" + p(r("Ohio State University")) + "</w:sdtContent></w:sdt>"
    assert word.extract(docx(tmp_path, body)) == "Ohio State University\n"


def test_strict_open_xml_reads_the_same(tmp_path):
    assert word.extract(docx(tmp_path, p(r("Alex Rivera")), ns=STRICT)) == "Alex Rivera\n"


def test_old_word_named_docx_says_save_as(tmp_path):
    path = tmp_path / "old.docx"
    path.write_bytes(b"\xd0\xcf\x11\xe0 old binary Word, or a password-locked docx")
    with pytest.raises(word.NotReadable, match="older Word file, or one locked with a password.*save a copy"):
        word.extract(path)


def test_file_told_by_first_bytes_not_name(tmp_path):
    renamed = tmp_path / "resume.docx"
    renamed.write_bytes(b"%PDF-1.7 ...")
    assert word.kind(renamed) == "pdf" and word.refusal(renamed) is None
    assert word.kind(docx(tmp_path, p(r("x")), name="resume.pdf")) == "word"


def test_template_prompt_text_moved_copy_and_nested_box_paragraphs(tmp_path):
    body = p(r("Ohio State University")) + \
        '<w:sdt><w:sdtPr><w:showingPlcHdr/></w:sdtPr><w:sdtContent>' + p(r("[Click to enter a date]")) + \
        '</w:sdtContent></w:sdt>' + \
        p('<w:moveFrom>' + r("Old place ") + '</w:moveFrom>', r("Kept line")) + \
        p(r("Certified"), f'<w:r><w:txbxContent>{p(r("Green Belt"))}</w:txbxContent></w:r>')
    assert word.extract(docx(tmp_path, body)).splitlines() == [
        "Ohio State University", "Kept line", "Certified", "Green Belt"]


def test_tab_stop_definitions_add_no_tab(tmp_path):
    body = '<w:p><w:pPr><w:tabs><w:tab w:val="right" w:pos="9360"/></w:tabs></w:pPr>' + r("Acme") + "</w:p>"
    assert word.extract(docx(tmp_path, body)) == "Acme\n"


@pytest.mark.skipif(sys.platform != "darwin" or not shutil.which("textutil"), reason="macOS textutil only")
def test_older_word_file_read_on_a_mac(tmp_path):
    source = docx(tmp_path, p(r("Alex Rivera")) + p(r("Scheduled 40 drivers across two depots")))
    old = tmp_path / "Resume.doc"
    subprocess.run(["textutil", "-convert", "doc", str(source), "-output", str(old)], check=True)
    assert word.kind(old) != "word" and word.refusal(old) is None
    assert word.read(old).splitlines() == ["Alex Rivera", "Scheduled 40 drivers across two depots"]


def test_zip_without_document_refused(tmp_path):
    path = tmp_path / "x.docx"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("hello.txt", "hi")
    with pytest.raises(word.NotReadable, match="no Word document"):
        word.extract(path)


def test_entity_declarations_refused(tmp_path):
    path = tmp_path / "bomb.docx"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", '<?xml version="1.0"?><!DOCTYPE d [<!ENTITY a "aaaa">]><d>&a;</d>')
    with pytest.raises(word.NotReadable, match="entities"):
        word.extract(path)


@pytest.mark.parametrize("name,what", [
    ("Resume.doc", "an older Word file"), ("Resume.pages", "a Pages file"), ("Resume.odt", "an OpenDocument file")])
def test_other_formats_get_one_plain_step(tmp_path, name, what, no_textutil):
    line = word.refusal(tmp_path / name)
    assert what in line and "save a copy as Word Document (.docx) or PDF" in line


def test_pdf_and_docx_pass(tmp_path):
    assert word.refusal(tmp_path / "a.PDF") is None and word.refusal(tmp_path / "a.docx") is None
