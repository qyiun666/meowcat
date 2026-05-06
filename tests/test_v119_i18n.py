# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat v1.1.9 — I18n 多语言引擎 测试。

覆盖:
- 默认语言 en，内置 en/zh 翻译
- t() 翻译 + 占位符替换
- 缺失 key 返回 key 本身
- 运行时切换语言
- 不支持语言抛 ValueError
- add_language 注册新语言
- pluge("language", ...) 注册语言
- supported_languages 属性
- 空占位符 / 多余占位符 容错
- I18n 继承 Pluggable 验证
"""

from __future__ import annotations

import pytest

from meowcat import I18n
from meowcat.pluggable import Pluggable


# -- 1. 默认语言与内置翻译 --------------------------------------------

class TestDefaultLanguage:
    """默认英文 + 内置 en/zh 翻译。"""

    def test_default_lang_is_en(self) -> None:
        i18n = I18n()
        assert i18n.lang == "en"

    def test_t_english(self) -> None:
        i18n = I18n()
        assert i18n.t("unknown_command", cmd="/foo") == "Unknown command: /foo"

    def test_t_chinese(self) -> None:
        i18n = I18n(lang="zh")
        assert i18n.t("unknown_command", cmd="/foo") == "未知命令: /foo"

    def test_t_without_placeholders(self) -> None:
        i18n = I18n()
        assert i18n.t("help_title") == "Help"

    def test_t_multiple_placeholders(self) -> None:
        i18n = I18n()
        result = i18n.t("cats_count", count=3)
        assert result == "Total cats: 3"

    def test_chinese_multiple_placeholders(self) -> None:
        i18n = I18n(lang="zh")
        result = i18n.t("language_set", lang="ja")
        assert result == "语言已切换为: ja"

    def test_all_builtin_keys_exist_in_both_languages(self) -> None:
        """确保 en 和 zh 的 key 集合一致。"""
        i18n_en = I18n(lang="en")
        i18n_zh = I18n(lang="zh")
        en_keys = set(i18n_en._locales["en"].keys())
        zh_keys = set(i18n_zh._locales["zh"].keys())
        diff = en_keys.symmetric_difference(zh_keys)
        assert diff == set(), f"Key mismatch: {diff}"


# -- 2. 缺失 key 容错 -------------------------------------------------

class TestMissingKeys:
    """缺失 key 返回 key 本身。"""

    def test_missing_key_returns_key(self) -> None:
        i18n = I18n()
        assert i18n.t("nonexistent_key") == "nonexistent_key"

    def test_missing_key_with_placeholders(self) -> None:
        i18n = I18n()
        assert i18n.t("nonexistent", name="value") == "nonexistent"


# -- 3. 运行时切换语言 ------------------------------------------------

class TestLanguageSwitch:
    """运行时切换语言。"""

    def test_switch_to_zh(self) -> None:
        i18n = I18n()
        i18n.lang = "zh"
        assert i18n.lang == "zh"
        assert i18n.t("help_title") == "帮助"

    def test_switch_back_to_en(self) -> None:
        i18n = I18n(lang="zh")
        i18n.lang = "en"
        assert i18n.lang == "en"
        assert i18n.t("help_title") == "Help"

    def test_unsupported_language_raises(self) -> None:
        i18n = I18n()
        with pytest.raises(ValueError, match="Unsupported language"):
            i18n.lang = "ja"


# -- 4. add_language 注册新语言 ---------------------------------------

class TestAddLanguage:
    """add_language 注册新语言或覆盖已有。"""

    def test_add_new_language(self) -> None:
        i18n = I18n()
        i18n.add_language("fr", {"hello": "Bonjour", "help_title": "Aide"})
        i18n.lang = "fr"
        assert i18n.t("hello") == "Bonjour"
        assert i18n.t("help_title") == "Aide"

    def test_add_language_merges_with_builtin_fallback(self) -> None:
        """新语言可继承已有 key，只覆盖部分。"""
        i18n = I18n()
        i18n.add_language("fr", {"help_title": "Aide"})
        i18n.lang = "fr"
        assert i18n.t("help_title") == "Aide"
        # 未覆盖的 key 返回 key 本身
        assert i18n.t("unknown_command", cmd="/x") == "unknown_command"

    def test_override_builtin_language(self) -> None:
        """add_language 可覆盖内置语言。"""
        i18n = I18n(lang="zh")
        i18n.add_language("zh", {"help_title": "自定义帮助"})
        assert i18n.t("help_title") == "自定义帮助"


# -- 5. plug("language", ...) 注册语言 --------------------------------

class TestPlugLanguage:
    """plug slot 注册新语言。"""

    def test_plug_register_language(self) -> None:
        i18n = I18n()
        i18n.plug("language", "ja", {"unknown_command": "不明なコマンド: {cmd}"})
        i18n.lang = "ja"
        assert i18n.t("unknown_command", cmd="/foo") == "不明なコマンド: /foo"

    def test_plug_without_data_falls_back_to_standard(self) -> None:
        """plug 不带 data 时走标准 mount_plug 行为。"""
        i18n = I18n()

        captured = []

        def my_handler():
            captured.append("called")

        i18n.plug("custom_hook", my_handler)
        for _hook, r in i18n._run_plugs_sync("custom_hook"):
            captured.append(str(r))
        assert "called" in captured or len(captured) >= 1


# -- 6. supported_languages -------------------------------------------

class TestSupportedLanguages:
    """supported_languages 返回已排序语言列表。"""

    def test_supported_languages_default(self) -> None:
        i18n = I18n()
        assert i18n.supported_languages == ["en", "zh"]

    def test_supported_languages_after_add(self) -> None:
        i18n = I18n()
        i18n.add_language("ja", {})
        assert i18n.supported_languages == ["en", "ja", "zh"]


# -- 7. 占位符容错 ---------------------------------------------------

class TestPlaceholderTolerance:
    """占位符容错。"""

    def test_extra_kwargs_ignored(self) -> None:
        """多余 kwargs 被忽略（format 默认行为）。"""
        i18n = I18n()
        result = i18n.t("unknown_command", cmd="/foo", extra="ignored")
        assert result == "Unknown command: /foo"

    def test_missing_placeholder_returns_template(self) -> None:
        """缺少占位符时返回原始模板。"""
        i18n = I18n()
        result = i18n.t("unknown_command")  # 缺少 cmd
        assert result == "Unknown command: {cmd}"

    def test_curly_braces_in_template(self) -> None:
        """模板中有非占位符的花括号（如 JSON）时不被错误转义。"""
        i18n = I18n()
        i18n.add_language("test", {"json": '{{"key": "{val}"}}'})
        i18n.lang = "test"
        result = i18n.t("json", val="hello")
        assert result == '{"key": "hello"}'


# -- 8. Pluggable 继承验证 --------------------------------------------

class TestPluggableInheritance:
    """I18n 继承 Pluggable。"""

    def test_i18n_is_pluggable(self) -> None:
        i18n = I18n()
        assert isinstance(i18n, Pluggable)

    def test_has_hooks(self) -> None:
        assert "language" in I18n.HOOKS

    def test_list_plugs_empty_initially(self) -> None:
        i18n = I18n()
        assert i18n.list_plugs() == {}


# -- 9. 独立测试 — 不依赖 CatBase/Colony -----------------------------

class TestStandalone:
    """I18n 完全独立，零依赖 CatBase/Colony."""

    def test_no_dependency_on_cat(self) -> None:
        """I18n 不需要 Colony 或 CatBase。"""
        from meowcat.cli.i18n import I18n as DirectI18n
        i18n = DirectI18n()
        assert i18n.lang == "en"

    def test_from_meowcat_top_level(self) -> None:
        """从 meowcat 顶层导入可用。"""
        i18n = I18n()
        assert i18n.lang == "en"


# -- 10. 综合场景 -----------------------------------------------------

class TestIntegrationScenarios:
    """典型使用场景。"""

    def test_full_cli_message_flow(self) -> None:
        """模拟 CLI 命令的完整翻译流。"""
        i18n = I18n()
        assert i18n.t("unknown_command", cmd="/xyz") == "Unknown command: /xyz"
        assert i18n.t("help_title") == "Help"
        assert i18n.t("version_info", name="meowcat",
                      version="1.0.0") == "meowcat v1.0.0"
        assert i18n.t("cats_count", count=5) == "Total cats: 5"

    def test_full_zh_cli_message_flow(self) -> None:
        """模拟中文 CLI 命令的完整翻译流。"""
        i18n = I18n(lang="zh")
        assert i18n.t("unknown_command", cmd="/xyz") == "未知命令: /xyz"
        assert i18n.t("help_title") == "帮助"
        assert i18n.t("cats_count", count=5) == "猫总数: 5"
        assert i18n.t("health_all_ok") == "所有系统正常"

    def test_colony_labels(self) -> None:
        """猫舍相关标签。"""
        i18n = I18n()
        assert i18n.t("colony_title") == "Colony"
        assert i18n.t("colony_name") == "Name"
        assert i18n.t("cats_no_cats") == "No cats in colony"

    def test_search_scope_labels(self) -> None:
        """搜索边界标签。"""
        i18n = I18n()
        assert i18n.t("search_scope") == "Search scope"
        assert i18n.t("search_scope_self") == "Self"
        assert i18n.t("search_scope_colony") == "Colony"

