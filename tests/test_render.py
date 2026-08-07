from pypdf import PdfReader

from autocv.models import CV
from autocv.render import build_context, build_pdf, render_typst, typst_quote


def test_typst_quote_echappe_guillemets_et_antislash():
    assert typst_quote('a "b" \\c') == '"a \\"b\\" \\\\c"'


def test_typst_quote_neutralise_le_balisage():
    # `#`, `@` et `*` sont significatifs en balisage Typst mais inertes dans une chaîne.
    assert typst_quote("#import @preview *gras*") == '"#import @preview *gras*"'


def test_build_context_assemble_les_intitules(minimal_cv):
    context = build_context(minimal_cv)
    assert context["heading"] == "Ada Lovelace | Analyst"
    assert context["jobs"][0]["heading"] == "Traductrice – Menabrea"
    assert context["education_lines"][0]["rest"] == "1840"


def test_build_context_omet_les_champs_de_contact_vides(minimal_cv):
    lines = build_context(minimal_cv)["contact_lines"]
    labels = [part.label for line in lines for part in line]
    assert "Ville :" in labels
    assert "Tél :" not in labels  # non renseigné dans la fixture
    assert len(lines) == 1  # ni LinkedIn ni Github : la seconde ligne disparaît


def test_sidebar_desactive_par_defaut(minimal_cv):
    assert build_context(minimal_cv)["sidebar"] is False
    minimal_cv.theme.sidebar_width = "30mm"
    assert build_context(minimal_cv)["sidebar"] is True


def test_la_marge_droite_absorbe_le_bandeau(minimal_cv):
    # Sans cela le texte passerait sous le bandeau décoratif.
    assert "right: 10mm," in render_typst(minimal_cv)

    minimal_cv.theme.sidebar_width = "30mm"
    assert "right: 10mm + 30mm," in render_typst(minimal_cv)


def test_render_typst_injecte_le_contenu(minimal_cv):
    source = render_typst(minimal_cv)
    assert '"Ada Lovelace | Analyst"' in source
    assert '"Premier algorithme publié."' in source
    assert 'link("mailto:ada@example.org"' in source


def test_render_typst_sans_experience_ni_formation():
    cv = CV.model_validate({"name": "Sans rien"})
    source = render_typst(cv)
    assert "Expérience Professionnelle" not in source
    assert "Formation" not in source


def test_build_pdf_produit_un_pdf_lisible(minimal_cv, tmp_path):
    pdf = build_pdf(minimal_cv, tmp_path / "cv.pdf", keep_typ=True)
    assert pdf.exists()
    assert pdf.with_suffix(".typ").exists()

    reader = PdfReader(pdf)
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    assert "Ada Lovelace" in text
    assert "Premier algorithme publié." in text


def test_build_pdf_survit_aux_caracteres_de_balisage(tmp_path):
    piege = "Coût #1 : 50% *net* _souligné_ @nom <tag> [ref] $x$ / a\\b"
    cv = CV.model_validate({"name": "Test", "skills": [{"label": "Piège", "text": piege}]})
    pdf = build_pdf(cv, tmp_path / "cv.pdf")

    text = PdfReader(pdf).pages[0].extract_text()
    assert "*net*" in text
    assert "@nom" in text
    assert "<tag>" in text
