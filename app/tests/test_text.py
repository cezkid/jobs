from text import html_to_text


def test_html_to_text_strips_tags_keeps_breaks():
    assert html_to_text("<p>One &amp; two</p><ul><li>Vue</li></ul>") == "One & two\n\nVue"


def test_html_to_text_drops_mojibake():
    assert "�" not in html_to_text("<p>Vue�Node</p>")
