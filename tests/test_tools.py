"""Tests para tool definitions — validación de esquemas para Claude."""

from src.tools.definitions import ALL_TOOLS, TOOL_NAMES


class TestToolDefinitions:
    def test_tool_count_is_16(self):
        assert len(ALL_TOOLS) == 16

    def test_no_duplicate_names(self):
        names = [t["name"] for t in ALL_TOOLS]
        assert len(names) == len(set(names))

    def test_tool_names_set_matches_list(self):
        names_from_list = {t["name"] for t in ALL_TOOLS}
        assert names_from_list == TOOL_NAMES

    def test_all_tools_have_required_fields(self):
        for tool in ALL_TOOLS:
            assert "name" in tool, f"Tool missing 'name'"
            assert "description" in tool, f"Tool {tool.get('name', '?')} missing 'description'"
            assert "input_schema" in tool, f"Tool {tool['name']} missing 'input_schema'"

    def test_input_schemas_are_valid(self):
        for tool in ALL_TOOLS:
            schema = tool["input_schema"]
            assert schema["type"] == "object", f"Tool {tool['name']} schema type is not 'object'"
            assert "properties" in schema, f"Tool {tool['name']} missing 'properties'"

    def test_required_fields_exist_in_properties(self):
        for tool in ALL_TOOLS:
            schema = tool["input_schema"]
            required = schema.get("required", [])
            properties = schema.get("properties", {})
            for field in required:
                assert field in properties, (
                    f"Tool {tool['name']}: required field '{field}' not in properties"
                )

    def test_expected_tools_present(self):
        """Verifica que las tools clave del bot estén definidas."""
        expected = [
            "buscar_paciente",
            "buscar_lead",
            "crear_lead",
            "agendar_turno",
            "consultar_tarifario",
            "registrar_pago",
            "crear_tarea_pendiente",
        ]
        for name in expected:
            assert name in TOOL_NAMES, f"Tool '{name}' not found in definitions"
