"""Tests para data_loader — carga de archivos .md para contexto de Claude."""

from src.utils.data_loader import (
    load_system_prompt,
    load_tratamientos,
    load_protocolos_quejas,
    build_full_system_prompt,
)


class TestLoadSystemPrompt:
    def test_loads_and_has_content(self):
        prompt = load_system_prompt()
        assert len(prompt) > 10000
        assert "Sofia" in prompt or "SOFIA" in prompt or "Sofía" in prompt

    def test_cached_returns_same_object(self):
        p1 = load_system_prompt()
        p2 = load_system_prompt()
        assert p1 is p2  # misma referencia = cache funciona


class TestLoadTratamientos:
    def test_loads_and_has_content(self):
        content = load_tratamientos()
        assert len(content) > 5000

    def test_contains_treatment_keywords(self):
        content = load_tratamientos()
        # Debe mencionar al menos algunos tratamientos de STICK
        assert any(
            word in content.lower()
            for word in ["alineadores", "brackets", "blanqueamiento", "ortodoncia"]
        )


class TestLoadProtocolosQuejas:
    def test_loads_and_has_content(self):
        content = load_protocolos_quejas()
        assert len(content) > 1000


class TestBuildFullSystemPrompt:
    def test_combines_all_parts(self):
        full = build_full_system_prompt()
        assert "TRATAMIENTOS" in full
        assert "QUEJAS" in full
        assert len(full) > 50000

    def test_longer_than_base_prompt(self):
        base = load_system_prompt()
        full = build_full_system_prompt()
        assert len(full) > len(base)
