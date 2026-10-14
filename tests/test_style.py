import json
import shutil
from pathlib import Path

import pytest

from deepwick_spec.ansi import runs, style_of
from deepwick_spec.check_port import check_port
from deepwick_spec.palette import load_palette
from deepwick_spec.tui import capture, tmux_available

REPO = Path(__file__).resolve().parents[1]
PALETTE = load_palette()
C = PALETTE.colors


STYLE = REPO / "deepwick.json"
SAMPLE = REPO.parent / "spec" / "samples" / "sample.md"
TOP_KEYS = {
    "document", "block_quote", "paragraph", "list", "heading", "h1", "h2", "h3", "h4", "h5", "h6", "text",
    "strikethrough", "emph", "strong", "hr", "item", "enumeration", "task", "link", "link_text", "image",
    "image_text", "code", "code_block", "table", "definition_list", "definition_term", "definition_description",
    "html_block", "html_span",
}
CHROMA = {
    "text": "foreground", "error": "red", "comment": "comment", "comment_preproc": "muted", "keyword": "blue",
    "keyword_reserved": "magenta", "keyword_namespace": "magenta", "keyword_type": "teal", "operator": "foreground",
    "punctuation": "foreground", "name": "lightBlue", "name_builtin": "yellow", "name_tag": "blue",
    "name_attribute": "lightBlue", "name_class": "teal", "name_constant": "cyan", "name_decorator": "yellow",
    "name_exception": "teal", "name_function": "yellow", "name_other": "lightBlue", "literal_number": "sage",
    "literal_string": "orange", "literal_string_escape": "gold", "generic_deleted": "red", "generic_inserted": "green",
    "generic_subheading": "blue",
}


def near(actual, expected):
    if not (actual or "").startswith("#"):
        return False
    return all(abs(int(actual[i : i + 2], 16) - int(expected[i : i + 2], 16)) <= 1 for i in (1, 3, 5))


def style():
    assert STYLE.is_file(), "deepwick.json missing"
    return json.loads(STYLE.read_text(encoding="utf-8"))


def test_complete_style():
    assert set(style()) == TOP_KEYS


def test_document_roles():
    s = style()
    assert s["document"]["color"] == C["foreground"]
    assert s["heading"]["color"] == C["blue"] and s["heading"]["bold"] is True
    assert s["h1"]["color"] == C["background"] and s["h1"]["background_color"] == C["blue"]
    assert s["link"]["color"] == C["orange"] and s["link_text"]["color"] == C["orange"]
    assert s["code"]["color"] == C["orange"] and s["code"]["background_color"] == C["surface"]
    assert s["block_quote"]["color"] == C["comment"] and s["block_quote"]["italic"] is True
    assert s["emph"] == {"italic": True} and s["strong"] == {"bold": True}


def test_chroma_follows_syntax_roles():
    chroma = style()["code_block"]["chroma"]
    for key, color in CHROMA.items():
        assert chroma[key]["color"] == C[color], key
    assert chroma["comment"]["italic"] is True
    assert chroma["background"] == {"background_color": C["surface"]}


@pytest.mark.skipif(not (tmux_available() and shutil.which("glow") and SAMPLE.is_file()), reason="requires tmux, glow, spec clone")
def test_glow_renders_sample(tmp_path):
    env = {"HOME": str(tmp_path / "home")}
    for kind in ("CONFIG", "DATA", "STATE", "CACHE"):
        env[f"XDG_{kind}_HOME"] = str(tmp_path / kind.lower())
    text = capture(f"glow -w 80 -s {STYLE} {SAMPLE}; sleep 30", env, size=(90, 60), wait_for="Deepwick")
    styles = [s for _, s in runs(text)]
    # glow rounds some 24-bit channels down by one (Foreground D4 renders as D3).
    assert any(near(s["fg"], C["foreground"]) for s in styles)
    assert any(s["fg"] == C["orange"].lower() for s in styles)
    assert any(s["bg"] == C["blue"].lower() and s["fg"] == C["background"].lower() for s in styles)
    assert any(s["italic"] for s in styles)


def test_port_conventions():
    assert check_port(REPO, PALETTE.allowed_hex()) == []


def test_readme_glow_yml_style_path_is_absolute():
    # glow passes the glow.yml style path to glamour unexpanded, so "~" or "$VAR" fails to load.
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    block = readme.split("```yaml\n", 1)[1].split("```", 1)[0]
    value = block.split("style:", 1)[1].strip().strip('"')
    assert value.startswith("/") and "~" not in value and "$" not in value, value
