from __future__ import annotations

import pytest

from app.agents.utils import (
    build_character_context,
    extract_json,
    _extract_first_complete_json,
    _fix_common_json_errors,
    _try_fix_incomplete_json,
)
from app.db.utils import utcnow
from types import SimpleNamespace


class TestExtractJson:
    def test_valid_json(self):
        text = '{"agent": "review", "score": 85}'
        result = extract_json(text)
        assert result == {"agent": "review", "score": 85}

    def test_json_with_markdown_fence(self):
        text = '```json\n{"agent": "review", "score": 85}\n```'
        result = extract_json(text)
        assert result == {"agent": "review", "score": 85}

    def test_json_with_surrounding_text(self):
        text = 'Here is the result:\n{"agent": "review", "score": 85}\nDone.'
        result = extract_json(text)
        assert result == {"agent": "review", "score": 85}

    def test_nested_json(self):
        text = '{"quality_report": {"score": 85, "issues": []}}'
        result = extract_json(text)
        assert result == {"quality_report": {"score": 85, "issues": []}}

    def test_json_with_unicode(self):
        text = '{"message": "审核完成", "score": 85}'
        result = extract_json(text)
        assert result == {"message": "审核完成", "score": 85}

    def test_no_json_raises(self):
        text = "This is just plain text without any JSON"
        with pytest.raises(ValueError, match="未找到有效的 JSON 对象"):
            extract_json(text)

    def test_array_raises(self):
        text = '[1, 2, 3]'
        with pytest.raises(ValueError, match="未找到有效的 JSON 对象"):
            extract_json(text)


class TestTryFixIncompleteJson:
    def test_missing_closing_brace(self):
        text = '{"agent": "review"'
        result = _try_fix_incomplete_json(text)
        assert result == '{"agent": "review"}'

    def test_missing_multiple_braces(self):
        text = '{"outer": {"inner": "value"'
        result = _try_fix_incomplete_json(text)
        assert result == '{"outer": {"inner": "value"}}'

    def test_missing_bracket(self):
        text = '{"items": [1, 2, 3'
        result = _try_fix_incomplete_json(text)
        assert result == '{"items": [1, 2, 3]}'

    def test_truncated_string(self):
        text = '{"message": "hello wor'
        result = _try_fix_incomplete_json(text)
        assert '"hello wor"' in result

    def test_complete_json_unchanged(self):
        text = '{"complete": true}'
        result = _try_fix_incomplete_json(text)
        assert result == '{"complete": true}'

    def test_escaped_quotes(self):
        text = '{"text": "say \\"hello\\""}'
        result = _try_fix_incomplete_json(text)
        assert result == '{"text": "say \\"hello\\""}'


class TestExtractJsonEdgeCases:
    def test_empty_object(self):
        text = '{}'
        result = extract_json(text)
        assert result == {}

    def test_whitespace_around_json(self):
        text = '   \n\n  {"key": "value"}  \n\n  '
        result = extract_json(text)
        assert result == {"key": "value"}

    def test_json_with_newlines(self):
        text = '''
        {
            "agent": "review",
            "score": 85
        }
        '''
        result = extract_json(text)
        assert result == {"agent": "review", "score": 85}

    def test_complex_nested_structure(self):
        text = '''
        {
            "quality_report": {
                "score": 85,
                "issues": [
                    {"severity": "low", "description": "Minor issue"}
                ]
            },
            "route": {
                "next_agent": "character",
                "reason": "Need to regenerate"
            }
        }
        '''
        result = extract_json(text)
        assert result["quality_report"]["score"] == 85
        assert result["route"]["next_agent"] == "character"
        assert len(result["quality_report"]["issues"]) == 1


class TestExtractFirstCompleteJson:
    def test_finds_json_in_text(self):
        text = 'Here is {"key": "value"} done'
        assert _extract_first_complete_json(text) == '{"key": "value"}'

    def test_no_opening_brace(self):
        assert _extract_first_complete_json("no json here") is None

    def test_unclosed_returns_remainder(self):
        text = '{"key": "value"'
        assert _extract_first_complete_json(text) == '{"key": "value"'

    def test_escaped_quotes_inside_string(self):
        text = r'{"key": "say \"hello\""}'
        assert _extract_first_complete_json(text) == r'{"key": "say \"hello\""}'

    def test_nested_objects(self):
        text = 'Prefix {"a": {"b": 1}} Suffix'
        assert _extract_first_complete_json(text) == '{"a": {"b": 1}}'


class TestFixCommonJsonErrors:
    def test_removes_line_comment(self):
        text = '{"a": 1 // comment\n}'
        result = _fix_common_json_errors(text)
        assert "// comment" not in result
        assert '"a"' in result

    def test_removes_block_comment(self):
        text = '{"a": /* block */ 1}'
        result = _fix_common_json_errors(text)
        assert "block" not in result

    def test_trailing_comma_object(self):
        text = '{"a": 1,}'
        result = _fix_common_json_errors(text)
        assert result == '{"a": 1}'

    def test_trailing_comma_array(self):
        text = '[1, 2,]'
        result = _fix_common_json_errors(text)
        assert result == '[1, 2]'

    def test_missing_comma_between_objects(self):
        text = '{"a": 1}\n{"b": 2}'
        result = _fix_common_json_errors(text)
        assert '},\n{' in result

    def test_missing_comma_between_strings(self):
        text = '"a"\n"b"'
        result = _fix_common_json_errors(text)
        assert '",\n"' in result

    def test_missing_comma_after_number(self):
        text = '123\n"key"'
        result = _fix_common_json_errors(text)
        assert '123,\n"key"' in result

    def test_missing_comma_after_true(self):
        text = 'true\n"key"'
        result = _fix_common_json_errors(text)
        assert 'true,\n"key"' in result


class TestBuildCharacterContext:
    def test_with_description(self):
        chars = [SimpleNamespace(name="Alice", description="brave warrior")]
        result = build_character_context(chars)
        assert result == "Characters: Alice: brave warrior"

    def test_without_description(self):
        chars = [SimpleNamespace(name="Bob", description=None)]
        result = build_character_context(chars)
        assert result == "Characters: Bob"

    def test_empty_list(self):
        assert build_character_context([]) == ""

    def test_multiple_chars(self):
        chars = [
            SimpleNamespace(name="Alice", description="brave"),
            SimpleNamespace(name="Bob", description=None),
        ]
        result = build_character_context(chars)
        assert "Alice: brave" in result
        assert "Bob" in result


class TestUtcnow:
    def test_returns_naive_datetime(self):
        dt = utcnow()
        assert dt.tzinfo is None


class TestExtractJsonThinkTag:
    def test_think_tag(self):
        text = '<think>\n{"wrong": true}\n</think>\n{"correct": true}'
        result = extract_json(text)
        assert result == {"correct": True}

    def test_thinking_tag(self):
        text = '<thinking>{"wrong": true}</thinking>{"correct": true}'
        result = extract_json(text)
        assert result == {"correct": True}
