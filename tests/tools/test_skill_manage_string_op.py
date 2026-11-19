"""An operations[] element that is a string (a JSON-encoded array that failed to parse) gets an
error naming the real problem, not "needs an 'action'"."""

import json

from tools import skill_manager_tool


def test_string_operation_reports_invalid_json_not_missing_action():
    broken = '[{"action": "create" "name": "probe"}]'  # missing comma: not valid JSON

    result = json.loads(skill_manager_tool.skill_manage(action="", name="", operations=[broken]))

    assert result["success"] is False
    assert "needs an 'action'" not in result["error"]
    assert "not valid JSON" in result["error"]
