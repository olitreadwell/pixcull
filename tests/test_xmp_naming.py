"""Sidecar naming: Lightroom says `A.xmp`, darktable says `A.ARW.xmp`.

darktable reads a Lightroom-style sidecar on import, then writes its own
`<name>.<ext>.xmp` next to it, so a shoot ends up with two files that
drift apart. `naming="darktable"` writes and updates that one instead —
in place, because a darktable sidecar carries the develop history and
rewriting the packet would throw it away.
"""

from __future__ import annotations

from pathlib import Path

from pixcull.io.xmp import write_xmp

_HISTORY = (
    '<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
    '<x:xmpmeta xmlns:x="adobe:ns:meta/">\n'
    ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">\n'
    '  <rdf:Description rdf:about=""\n'
    '    xmlns:xmp="http://ns.adobe.com/xap/1.0/"\n'
    '    xmlns:darktable="http://darktable.sf.net/"\n'
    '    xmp:Rating="0">\n'
    '   <darktable:history>\n'
    '    <rdf:Seq><rdf:li>exposure 1.20</rdf:li></rdf:Seq>\n'
    '   </darktable:history>\n'
    '  </rdf:Description>\n'
    ' </rdf:RDF>\n'
    '</x:xmpmeta>\n'
)


def _image(tmp_path: Path, name: str = "A.ARW") -> Path:
    p = tmp_path / name
    p.write_bytes(b"raw")
    return p


def test_lightroom_naming_is_unchanged(tmp_path):
    out = write_xmp(_image(tmp_path), 5, "Green")
    assert out.name == "A.xmp"


def test_darktable_naming_uses_the_full_filename(tmp_path):
    out = write_xmp(_image(tmp_path), 5, "Green", naming="darktable")
    assert out.name == "A.ARW.xmp"
    assert (tmp_path / "A.xmp").exists() is False


def test_darktable_sidecar_is_patched_not_replaced(tmp_path):
    img = _image(tmp_path)
    sidecar = tmp_path / "A.ARW.xmp"
    sidecar.write_text(_HISTORY, encoding="utf-8")

    out = write_xmp(img, 5, "Green", naming="darktable", preserve_existing=False)

    assert out == sidecar
    text = sidecar.read_text(encoding="utf-8")
    assert 'xmp:Rating="5"' in text
    assert "exposure 1.20" in text, "darktable develop history was destroyed"
    assert "darktable:history" in text


def test_patch_writes_the_label_when_absent(tmp_path):
    img = _image(tmp_path)
    sidecar = tmp_path / "A.ARW.xmp"
    sidecar.write_text(_HISTORY, encoding="utf-8")

    write_xmp(img, 5, "Green", naming="darktable", preserve_existing=False)

    text = sidecar.read_text(encoding="utf-8")
    assert ('xmp:Label="Green"' in text) or ("<xmp:Label>Green</xmp:Label>" in text)


def test_patch_keeps_element_form_when_that_is_what_is_there(tmp_path):
    img = _image(tmp_path)
    sidecar = tmp_path / "A.ARW.xmp"
    sidecar.write_text(
        _HISTORY.replace('xmp:Rating="0"', "")
        .replace("</rdf:Description>",
                 "  <xmp:Rating>0</xmp:Rating>\n  </rdf:Description>"),
        encoding="utf-8")

    write_xmp(img, 3, "", naming="darktable", preserve_existing=False)

    text = sidecar.read_text(encoding="utf-8")
    assert "<xmp:Rating>3</xmp:Rating>" in text
    assert "exposure 1.20" in text


def test_preserve_reads_the_sidecar_it_writes(tmp_path):
    """A star set inside darktable lives in `<name>.<ext>.xmp`. PixCull's
    preserve rule must read that one, not a stale Lightroom sidecar."""
    img = _image(tmp_path)
    (tmp_path / "A.ARW.xmp").write_text(
        _HISTORY.replace('xmp:Rating="0"', 'xmp:Rating="4"'), encoding="utf-8")

    write_xmp(img, 5, "Red", naming="darktable")

    text = (tmp_path / "A.ARW.xmp").read_text(encoding="utf-8")
    assert 'xmp:Rating="4"' in text, "the photographer's own star was overwritten"


def test_patch_updates_keywords_so_a_rerun_is_not_stale(tmp_path):
    img = _image(tmp_path)
    sidecar = tmp_path / "A.ARW.xmp"
    sidecar.write_text(_HISTORY, encoding="utf-8")

    write_xmp(img, 1, "Red", keywords=["PixCull:cull", "PixCull:scene:portrait"],
              naming="darktable", preserve_existing=False)

    text = sidecar.read_text(encoding="utf-8")
    assert "PixCull:cull" in text
    assert "PixCull:keep" not in text
    assert "exposure 1.20" in text


def test_patch_updates_the_caption(tmp_path):
    img = _image(tmp_path)
    sidecar = tmp_path / "A.ARW.xmp"
    sidecar.write_text(_HISTORY, encoding="utf-8")

    write_xmp(img, 3, "Yellow", description="Soft focus on the eyes.",
              naming="darktable", preserve_existing=False)

    text = sidecar.read_text(encoding="utf-8")
    assert "Soft focus on the eyes." in text
    assert "exposure 1.20" in text


def test_rerun_replaces_pixculls_own_star(tmp_path):
    """A second run must be able to move a photo from keep to cull. The
    previous star is only protected when PixCull did not put it there."""
    img = _image(tmp_path)
    write_xmp(img, 5, "Green", keywords=["PixCull:keep"], naming="darktable")
    write_xmp(img, 1, "Red", keywords=["PixCull:cull"], naming="darktable")

    text = (tmp_path / "A.ARW.xmp").read_text(encoding="utf-8")
    assert ('xmp:Rating="1"' in text) or ("<xmp:Rating>1</xmp:Rating>" in text)
    assert "PixCull:cull" in text
    assert "PixCull:keep" not in text


def test_default_naming_can_come_from_the_environment(tmp_path, monkeypatch):
    """A darktable user should not have to remember a flag on every run,
    including exports started from the web workspace."""
    from pixcull.io.xmp import default_xmp_naming

    monkeypatch.setenv("PIXCULL_XMP_NAMING", "darktable")
    assert default_xmp_naming() == "darktable"

    monkeypatch.setenv("PIXCULL_XMP_NAMING", "nonsense")
    assert default_xmp_naming() == "lightroom"

    monkeypatch.delenv("PIXCULL_XMP_NAMING")
    assert default_xmp_naming() == "lightroom"
