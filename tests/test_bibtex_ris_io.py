"""BibTeX/RIS 导入导出测试。"""

import pytest

from src.literature.bibtex_ris_io import (
    BibEntry,
    parse_bibtex,
    parse_ris,
    entries_to_bibtex,
    entries_to_ris,
)


SAMPLE_BIBTEX = """@article{wang2023anxiety,
  title = {Anxiety and Academic Burnout Among College Students},
  author = {Wang, Lei and Li, Ming},
  year = {2023},
  journal = {Journal of Psychology},
  volume = {45},
  number = {3},
  pages = {123-135},
  doi = {10.1234/jp.2023.001},
}

@article{li2022selfesteem,
  title = {Self-esteem as Mediator},
  author = {Li, Hua},
  year = {2022},
  journal = {Psychological Research},
  volume = {12},
  pages = {45-56},
}
"""

SAMPLE_RIS = """TY  - JOUR
ID  - wang2023
TI  - Anxiety and Academic Burnout
AU  - Wang, Lei
AU  - Li, Ming
PY  - 2023
JO  - Journal of Psychology
VL  - 45
IS  - 3
SP  - 123
EP  - 135
DO  - 10.1234/jp.2023.001
KW  - anxiety
KW  - burnout
ER  -

TY  - BOOK
TI  - Psychology of Learning
AU  - Zhang, Wei
PY  - 2021
ER  -
"""


class TestBibTeXParsing:
    def test_parse_basic_entries(self):
        entries = parse_bibtex(SAMPLE_BIBTEX)
        assert len(entries) == 2

    def test_parse_first_entry_fields(self):
        entries = parse_bibtex(SAMPLE_BIBTEX)
        e = entries[0]
        assert e.citation_key == "wang2023anxiety"
        assert e.entry_type == "article"
        assert "Anxiety" in e.title
        assert "Wang" in e.author
        assert e.year == "2023"
        assert e.journal == "Journal of Psychology"
        assert e.volume == "45"
        assert e.doi == "10.1234/jp.2023.001"

    def test_parse_second_entry(self):
        entries = parse_bibtex(SAMPLE_BIBTEX)
        e = entries[1]
        assert e.citation_key == "li2022selfesteem"
        assert e.year == "2022"

    def test_parse_empty_returns_empty(self):
        entries = parse_bibtex("")
        assert entries == []


class TestRISParsing:
    def test_parse_basic_entries(self):
        entries = parse_ris(SAMPLE_RIS)
        assert len(entries) == 2

    def test_parse_first_entry_fields(self):
        entries = parse_ris(SAMPLE_RIS)
        e = entries[0]
        assert e.citation_key == "wang2023"
        assert e.entry_type == "article"
        assert "Anxiety" in e.title
        assert "Wang, Lei" in e.author
        assert "Li, Ming" in e.author
        assert e.year == "2023"
        assert e.volume == "45"
        assert e.pages == "123-135"
        assert e.doi == "10.1234/jp.2023.001"
        assert "anxiety" in e.keywords

    def test_parse_book_type(self):
        entries = parse_ris(SAMPLE_RIS)
        e = entries[1]
        assert e.entry_type == "book"
        assert "Zhang" in e.author
        assert e.year == "2021"

    def test_parse_empty_returns_empty(self):
        entries = parse_ris("")
        assert entries == []

    def test_multiple_authors_joined(self):
        entries = parse_ris(SAMPLE_RIS)
        assert " and " in entries[0].author


class TestBibTeXExport:
    def test_roundtrip_bibtex(self):
        entries = parse_bibtex(SAMPLE_BIBTEX)
        exported = entries_to_bibtex(entries)
        re_parsed = parse_bibtex(exported)
        assert len(re_parsed) == 2
        assert re_parsed[0].citation_key == "wang2023anxiety"
        assert re_parsed[0].title == entries[0].title

    def test_single_entry_export(self):
        entry = BibEntry(
            entry_type="article",
            citation_key="test2024",
            title="Test Title",
            author="Author, A",
            year="2024",
        )
        text = entry.to_bibtex()
        assert "@article{test2024," in text
        assert "title = {Test Title}" in text


class TestRISExport:
    def test_export_basic(self):
        entries = [BibEntry(
            entry_type="article",
            citation_key="test2024",
            title="Test Article",
            author="Wang, Lei and Li, Hua",
            year="2024",
            journal="Test Journal",
        )]
        text = entries_to_ris(entries)
        assert "TY  - JOUR" in text
        assert "TI  - Test Article" in text
        assert "AU  - Wang, Lei" in text
        assert "AU  - Li, Hua" in text
        assert "PY  - 2024" in text
        assert "ER  - " in text

    def test_roundtrip_ris(self):
        entries = parse_ris(SAMPLE_RIS)
        exported = entries_to_ris(entries)
        re_parsed = parse_ris(exported)
        assert len(re_parsed) == 2
        assert re_parsed[0].title == entries[0].title
