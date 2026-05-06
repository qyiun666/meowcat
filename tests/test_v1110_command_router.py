# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat v1.1.10 — CommandRouter 命令路由注册框架 测试。

覆盖:
- Command 数据类创建
- CommandContext 上下文构建
- CommandRouter 注册/注销/查找
- route 精确匹配路由
- route 未知命令返回 i18n 错误
- 带参数命令路由
- middleware 中间件拦截
- list_commands / list_groups 分组
- 空输入 / 非 / 开头输入
- I18n 集成（中英文错误消息）
- Pluggable 继承验证
- 独立测试（零 CatBase/Colony 依赖）
"""

from __future__ import annotations

import pytest

from meowcat import Command, CommandContext, CommandRouter, I18n
from meowcat.pluggable import Pluggable


# -- 1. Command 数据类 -------------------------------------------------

class TestCommandDataClass:
    """Command 数据类创建与默认值。"""

    def test_create_minimal(self) -> None:
        cmd = Command(name="/test", handler=lambda ctx: "ok")
        assert cmd.name == "/test"
        assert cmd.group == "General"
        assert cmd.description == ""

    def test_create_full(self) -> None:
        cmd = Command(
            name="/health",
            handler=lambda ctx: "healthy",
            group="System",
            description="Check system health",
        )
        assert cmd.name == "/health"
        assert cmd.group == "System"
        assert cmd.description == "Check system health"


# -- 2. CommandContext 数据类 ------------------------------------------

class TestCommandContext:
    """CommandContext 创建。"""

    def test_defaults(self) -> None:
        router = CommandRouter()
        ctx = CommandContext(router=router, name="/test")
        assert ctx.args == ""
        assert ctx.raw_input == ""
        assert ctx.i18n is None

    def test_with_i18n(self) -> None:
        router = CommandRouter()
        i18n = I18n()
        ctx = CommandContext(router=router, name="/help", args="verbose",
                             raw_input="/help verbose", i18n=i18n)
        assert ctx.name == "/help"
        assert ctx.args == "verbose"
        assert ctx.raw_input == "/help verbose"
        assert ctx.i18n is i18n


# -- 3. CommandRouter 注册与注销 ---------------------------------------

class TestRegistration:
    """CommandRouter 注册/注销/查找。"""

    def test_register_and_get(self) -> None:
        router = CommandRouter()
        cmd = Command(name="/ping", handler=lambda ctx: "pong")
        router.register(cmd)
        assert router.get_command("/ping") is cmd

    def test_register_overwrites(self) -> None:
        router = CommandRouter()
        cmd1 = Command(name="/x", handler=lambda ctx: "v1")
        cmd2 = Command(name="/x", handler=lambda ctx: "v2")
        router.register(cmd1)
        router.register(cmd2)
        assert router.get_command("/x") is cmd2

    def test_unregister(self) -> None:
        router = CommandRouter()
        router.register(Command(name="/rm", handler=lambda ctx: "bye"))
        router.unregister("/rm")
        assert router.get_command("/rm") is None

    def test_unregister_missing_does_not_raise(self) -> None:
        router = CommandRouter()
        router.unregister("/nonexistent")  # no error

    def test_get_command_missing(self) -> None:
        router = CommandRouter()
        assert router.get_command("/nope") is None


# -- 4. 路由匹配 -------------------------------------------------------

class TestRouting:
    """route 方法路由匹配。"""

    async def test_exact_match(self) -> None:
        router = CommandRouter()
        router.register(Command(name="/hello", handler=lambda ctx: "world"))
        assert await router.route("/hello") == "world"

    async def test_unknown_command(self) -> None:
        router = CommandRouter()
        result = await router.route("/unknown")
        assert "unknown_command" in result

    async def test_unknown_command_with_i18n_en(self) -> None:
        router = CommandRouter(i18n=I18n())
        result = await router.route("/xyz")
        assert result == "Unknown command: /xyz"

    async def test_unknown_command_with_i18n_zh(self) -> None:
        router = CommandRouter(i18n=I18n(lang="zh"))
        result = await router.route("/xyz")
        assert result == "未知命令: /xyz"

    async def test_with_args(self) -> None:
        router = CommandRouter()
        captured = {}

        def handler(ctx: CommandContext) -> str:
            captured["args"] = ctx.args
            captured["raw"] = ctx.raw_input
            return f"got: {ctx.args}"

        router.register(Command(name="/echo", handler=handler))
        result = await router.route("/echo hello world")
        assert result == "got: hello world"
        assert captured["args"] == "hello world"
        assert captured["raw"] == "/echo hello world"

    async def test_empty_input(self) -> None:
        router = CommandRouter()
        result = await router.route("")
        assert "unknown_command" in result

    async def test_non_slash_input(self) -> None:
        router = CommandRouter()
        result = await router.route("hello")
        assert "unknown_command" in result


# -- 5. Middleware 中间件 ----------------------------------------------

class TestMiddleware:
    """middleware 中间件拦截。"""

    async def test_middleware_passes_through(self) -> None:
        """中间件返回 None 时继续执行 handler。"""
        router = CommandRouter()
        called = []

        def mw(ctx: CommandContext) -> None:
            called.append("mw")
            return None

        router.plug("middleware", mw)
        router.register(Command(name="/go", handler=lambda ctx: "done"))
        assert await router.route("/go") == "done"
        assert called == ["mw"]

    async def test_middleware_short_circuits(self) -> None:
        """中间件返回非 None 值时短路，不执行 handler。"""
        router = CommandRouter()
        handler_called = False

        def mw(ctx: CommandContext) -> str:
            return "blocked by middleware"

        router.plug("middleware", mw)
        router.register(
            Command(name="/secret", handler=lambda ctx: setattr(
                type(ctx), "_flag", True) or "exposed")
        )
        result = await router.route("/secret")
        assert result == "blocked by middleware"

    async def test_multiple_middleware_first_wins(self) -> None:
        """多个中间件，第一个非 None 短路。"""
        router = CommandRouter()

        def mw1(ctx: CommandContext) -> str:
            return "first"

        def mw2(ctx: CommandContext) -> str:
            return "second"

        router.plug("middleware", mw1)
        router.plug("middleware", mw2)
        router.register(Command(name="/x", handler=lambda ctx: "handler"))
        assert await router.route("/x") == "first"


# -- 6. 命令列表与分组 ------------------------------------------------

class TestListing:
    """list_commands / list_groups。"""

    def test_list_commands_empty(self) -> None:
        router = CommandRouter()
        assert router.list_commands() == []

    def test_list_commands(self) -> None:
        router = CommandRouter()
        router.register(Command(name="/a", handler=lambda ctx: "a"))
        router.register(Command(name="/b", handler=lambda ctx: "b"))
        cmds = router.list_commands()
        assert len(cmds) == 2
        names = {c.name for c in cmds}
        assert names == {"/a", "/b"}

    def test_list_groups(self) -> None:
        router = CommandRouter()
        router.register(Command(name="/sys1", handler=lambda ctx: "ok",
                                group="System"))
        router.register(Command(name="/gen1", handler=lambda ctx: "ok",
                                group="General"))
        router.register(Command(name="/sys2", handler=lambda ctx: "ok",
                                group="System"))
        groups = router.list_groups()
        assert set(groups.keys()) == {"System", "General"}
        assert len(groups["System"]) == 2
        assert len(groups["General"]) == 1


# -- 7. 异常处理 -------------------------------------------------------

class TestErrorHandling:
    """handler 异常处理。"""

    async def test_handler_raises_returns_error_message(self) -> None:
        router = CommandRouter(i18n=I18n())

        def broken(ctx: CommandContext) -> str:
            raise ValueError("boom")

        router.register(Command(name="/crash", handler=broken))
        result = await router.route("/crash")
        assert "command_error" in result or "boom" in result

    async def test_handler_raises_without_i18n(self) -> None:
        """无 i18n 时的错误降级处理。"""
        router = CommandRouter()

        def broken(ctx: CommandContext) -> str:
            raise RuntimeError("fail")

        router.register(Command(name="/fail", handler=broken))
        result = await router.route("/fail")
        assert "command_error" in result or "fail" in result


# -- 8. Pluggable 继承验证 ---------------------------------------------

class TestPluggableInheritance:
    """CommandRouter 继承 Pluggable。"""

    def test_is_pluggable(self) -> None:
        router = CommandRouter()
        assert isinstance(router, Pluggable)

    def test_has_middleware_hook(self) -> None:
        assert "middleware" in CommandRouter.HOOKS

    def test_list_plugs_empty_initially(self) -> None:
        router = CommandRouter()
        assert router.list_plugs() == {}


# -- 9. 独立测试 -------------------------------------------------------

class TestStandalone:
    """CommandRouter 完全独立，零依赖 CatBase/Colony."""

    async def test_no_dependency_on_cat(self) -> None:
        from meowcat.cli.router import CommandRouter as DirectRouter
        router = DirectRouter()
        router.register(Command(name="/x", handler=lambda ctx: "y"))
        assert await router.route("/x") == "y"

    async def test_from_meowcat_top_level(self) -> None:
        router = CommandRouter()
        router.register(Command(name="/top", handler=lambda ctx: "level"))
        assert await router.route("/top") == "level"


# -- 10. 综合场景 ------------------------------------------------------

class TestIntegrationScenarios:
    """综合使用场景。"""

    async def test_help_command_no_i18n(self) -> None:
        """模拟 /help 命令，输出命令列表。"""
        router = CommandRouter()

        def help_handler(ctx: CommandContext) -> str:
            cmds = ctx.router.list_commands()
            return ", ".join(c.name for c in cmds)

        router.register(Command(name="/help", handler=help_handler,
                                group="General", description="Show help"))
        router.register(Command(name="/version", handler=lambda ctx: "1.0.0",
                                group="System", description="Show version"))

        result = await router.route("/help")
        assert "/help" in result
        assert "/version" in result

    async def test_full_cli_flow_with_i18n(self) -> None:
        """模拟完整 CLI 命令流 + 中英文。"""
        i18n = I18n(lang="zh")
        router = CommandRouter(i18n=i18n)

        router.register(Command(name="/hello", handler=lambda ctx: "你好！"))
        router.register(Command(name="/bye", handler=lambda ctx: "再见！"))

        assert await router.route("/hello") == "你好！"
        assert await router.route("/bye") == "再见！"
        assert await router.route("/nope") == "未知命令: /nope"

    async def test_middleware_logging(self) -> None:
        """中间件记录所有命令调用。"""
        log = []

        def logger(ctx: CommandContext) -> None:
            log.append(ctx.name)
            return None

        router = CommandRouter()
        router.plug("middleware", logger)
        router.register(Command(name="/a", handler=lambda ctx: "A"))
        router.register(Command(name="/b", handler=lambda ctx: "B"))

        await router.route("/a")
        await router.route("/b")
        await router.route("/a")

        assert log == ["/a", "/b", "/a"]

