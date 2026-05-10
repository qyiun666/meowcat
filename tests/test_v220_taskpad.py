# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""Tests for v2.2.0: TaskPad + do_task + spawn_worker."""

import pytest

from meowcat.biology.task_pad import TaskItem, TaskPad, TaskPadStatus
from meowcat.defaults.factory import create_cat
from meowcat.testing import make_test_colony
from meowcat.tools.tool import Tool, ToolSpec
from meowcat.tools.tool_call import DoTaskResult, ToolCall, XmlToolCallParser

# ── TaskPad tests ──────────────────────────────────────────────────


class TestTaskPad:
    def test_post_task(self):
        pad = TaskPad()
        item = pad.post("写一个函数")
        assert isinstance(item, TaskItem)
        assert item.content == "写一个函数"
        assert item.status == TaskPadStatus.TODO
        assert item.result == ""
        assert item.created_at is not None
        assert len(item.task_id) == 12  # uuid hex[:12]

    def test_empty_pad(self):
        pad = TaskPad()
        assert pad.is_empty()
        assert pad.pick() is None
        assert pad.list_todo() == []
        assert pad.list_all() == []
        assert pad.count() == 0

    def test_pick_fifo(self):
        pad = TaskPad()
        a = pad.post("任务A")
        b = pad.post("任务B")
        picked = pad.pick()
        assert picked is not None
        assert picked.task_id == a.task_id

    def test_pick_skips_done(self):
        pad = TaskPad()
        a = pad.post("任务A")
        b = pad.post("任务B")
        pad.mark_done(a.task_id)
        picked = pad.pick()
        assert picked is not None
        assert picked.task_id == b.task_id

    def test_mark_done(self):
        pad = TaskPad()
        item = pad.post("任务")
        pad.mark_done(item.task_id, "完成了")
        assert item.status == TaskPadStatus.DONE
        assert item.result == "完成了"
        assert item.done_at is not None

    def test_mark_doing(self):
        pad = TaskPad()
        item = pad.post("任务")
        pad.mark_doing(item.task_id)
        assert item.status == TaskPadStatus.DOING

    def test_mark_failed(self):
        pad = TaskPad()
        item = pad.post("任务")
        pad.mark_failed(item.task_id, "出错了")
        assert item.status == TaskPadStatus.FAILED
        assert item.result == "出错了"
        assert item.done_at is not None

    def test_list_todo_only(self):
        pad = TaskPad()
        a = pad.post("A")
        b = pad.post("B")
        pad.mark_done(a.task_id)
        todos = pad.list_todo()
        assert len(todos) == 1
        assert todos[0].task_id == b.task_id

    def test_diagnose(self):
        pad = TaskPad(max_tasks=10)
        pad.post("任务")
        pad.post("任务2")
        diag = pad.diagnose()
        assert diag["count"] == 2
        assert diag["max_tasks"] == 10
        assert diag["by_status"]["todo"] == 2

    def test_max_capacity_raises(self):
        pad = TaskPad(max_tasks=2)
        pad.post("A")
        pad.post("B")
        with pytest.raises(ValueError, match="full"):
            pad.post("C")

    def test_find_not_found_raises(self):
        pad = TaskPad()
        with pytest.raises(ValueError, match="not found"):
            pad.mark_done("nonexistent")

    def test_count_by_status(self):
        pad = TaskPad()
        pad.post("A")
        b = pad.post("B")
        pad.mark_done(b.task_id)
        statuses = pad.count_by_status()
        assert statuses["todo"] == 1
        assert statuses["done"] == 1
        assert statuses["doing"] == 0
        assert statuses["failed"] == 0


# ── ToolCall / Parser tests ────────────────────────────────────────


class TestToolCall:
    def test_basic(self):
        tc = ToolCall(name="read", params={"path": "/x"})
        assert tc.name == "read"
        assert tc.params == {"path": "/x"}

    def test_default_params(self):
        tc = ToolCall(name="ping")
        assert tc.params == {}


class TestDoTaskResult:
    def test_basic(self):
        tr = DoTaskResult(final_text="done", rounds=3)
        assert tr.final_text == "done"
        assert tr.rounds == 3
        assert tr.tool_calls == []

    def test_with_tool_calls(self):
        tc = ToolCall(name="read", params={"path": "/x"})
        tr = DoTaskResult(final_text="ok", rounds=5, tool_calls=[tc])
        assert len(tr.tool_calls) == 1
        assert tr.tool_calls[0].name == "read"


class TestXmlToolCallParser:
    def setup_method(self):
        self.parser = XmlToolCallParser()

    def test_no_tool_tag_returns_none(self):
        assert self.parser.extract("这是普通文本") is None

    def test_basic_tool(self):
        tc = self.parser.extract(
            '<tool name="read_file"><param name="path">/tmp/x.py</param></tool>'
        )
        assert tc is not None
        assert tc.name == "read_file"
        assert tc.params == {"path": "/tmp/x.py"}

    def test_multiple_params(self):
        tc = self.parser.extract(
            '<tool name="search">'
            '<param name="query">hello world</param>'
            '<param name="limit">10</param>'
            "</tool>"
        )
        assert tc is not None
        assert tc.params == {"query": "hello world", "limit": "10"}

    def test_case_insensitive(self):
        tc = self.parser.extract(
            '<TOOL name="READ"><param name="X">V</param></TOOL>'
        )
        assert tc is not None
        assert tc.name == "READ"
        assert tc.params == {"X": "V"}

    def test_multiline(self):
        tc = self.parser.extract(
            """好的，我来读取文件。
            <tool name="read">
              <param name="path">/tmp/test.py</param>
            </tool>
            请稍等..."""
        )
        assert tc is not None
        assert tc.name == "read"

    def test_no_params(self):
        tc = self.parser.extract('<tool name="status"></tool>')
        assert tc is not None
        assert tc.name == "status"
        assert tc.params == {}


# ── do_task tests ──────────────────────────────────────────────────


class TestDoTask:
    """Test cat.do_task() with a fake cerebrum."""

    def _make_echo_cat(self):
        """Create a cat whose cerebrum echoes input back."""
        colony = make_test_colony("dotask")

        class EchoCerebrum:
            name = "echo"

            async def generate(self, prompt, system_prompt=None,
                               temperature=0.7, max_tokens=None):
                return f"回复: {prompt}"

            async def stream_generate(self, prompt, system_prompt=None,
                                      temperature=0.7, max_tokens=None):
                yield f"回复: {prompt}"

            def reload_config(self):
                pass

        return create_cat(name="echo-cat", container=colony, cerebrum=EchoCerebrum())

    @pytest.mark.anyio
    async def test_no_tool_needed(self):
        """大脑返回纯文本 → 1 轮结束"""
        cat = self._make_echo_cat()
        result = await cat.do_task("简单任务")
        assert isinstance(result, DoTaskResult)
        assert result.rounds == 1
        assert result.tool_calls == []
        assert "回复:" in result.final_text

    @pytest.mark.anyio
    async def test_xml_parser_no_tag_returns_none(self):
        """大脑返回普通文本（无 XML 工具标签）→ 解析器返回 None → 循环结束"""
        cat = self._make_echo_cat()
        result = await cat.do_task("不需要工具的任务", max_rounds=5)
        assert result.rounds == 1
        assert result.tool_calls == []

    @pytest.mark.anyio
    async def test_max_rounds_cutoff(self):
        """工具调用不断循环直到 max_rounds → 截断"""
        colony = make_test_colony("dotask_loop")

        class LoopingCerebrum:
            """始终返回工具调用，永不停歇"""
            name = "looper"

            async def generate(self, prompt, system_prompt=None,
                               temperature=0.7, max_tokens=None):
                return '<tool name="echo"><param name="msg">hello</param></tool>'

            async def stream_generate(self, prompt, system_prompt=None,
                                      temperature=0.7, max_tokens=None):
                yield '<tool name="echo"><param name="msg">hello</param></tool>'

            def reload_config(self):
                pass

        cat = create_cat(name="looper-cat", container=colony,
                         cerebrum=LoopingCerebrum())

        # Register a fake tool so execute_tool doesn't fail
        cat.tool_registry.register(Tool(
            ToolSpec(name="echo", description="echo tool"), handler=self._fake_echo_tool))

        result = await cat.do_task("永不停止的任务", max_rounds=3)
        assert result.rounds == 3
        assert len(result.tool_calls) == 3

    async def _fake_echo_tool(self, msg: str = "", **kw):
        return {"echo": msg}

    @pytest.mark.anyio
    async def test_single_tool_call(self):
        """大脑先调用工具，然后返回最终回答"""
        colony = make_test_colony("dotask_tool")

        class ToolThenDoneCerebrum:
            call_count = 0
            name = "tooldone"

            async def generate(self, prompt, system_prompt=None,
                               temperature=0.7, max_tokens=None):
                self.call_count += 1
                if self.call_count == 1:
                    return '<tool name="calculator"><param name="expr">1+1</param></tool>'
                else:
                    return "结果是 2"

            async def stream_generate(self, prompt, system_prompt=None,
                                      temperature=0.7, max_tokens=None):
                self.call_count += 1
                if self.call_count == 1:
                    yield '<tool name="calculator"><param name="expr">1+1</param></tool>'
                else:
                    yield "结果是 2"

            def reload_config(self):
                pass

        cat = create_cat(name="tool-cat", container=colony,
                         cerebrum=ToolThenDoneCerebrum())

        # Register fake calculator tool
        cat.tool_registry.register(Tool(
            ToolSpec(name="calculator", description="计算表达式"),
            handler=self._fake_calculator,
        ))

        result = await cat.do_task("计算 1+1", max_rounds=10)
        assert result.rounds == 2
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "calculator"
        assert result.tool_calls[0].params["expr"] == "1+1"

    async def _fake_calculator(self, expr: str = "", **kw):
        return {"result": eval(expr)}  # noqa: S307 — test-only, 安全


class TestSpawnWorker:
    """Test cat.spawn_worker()"""

    def test_spawn_creates_cat(self):
        colony = make_test_colony("spawn")
        cat = colony.create_cat(name="main")

        worker = cat.spawn_worker("helper", "帮我查一下资料")

        assert worker.name == "helper"
        assert worker.cat_uid is not None
        assert worker.cat_uid != cat.cat_uid

    def test_parent_id_set(self):
        colony = make_test_colony("spawn2")
        cat = colony.create_cat(name="main")

        worker = cat.spawn_worker("helper", "子任务")

        assert worker.parent_id == cat.cat_uid

    def test_task_pad_created_and_has_task(self):
        colony = make_test_colony("spawn3")
        cat = colony.create_cat(name="main")

        worker = cat.spawn_worker("helper", "检索代码")

        assert worker.task_pad is not None
        assert not worker.task_pad.is_empty()
        assert worker.task_pad.count() == 1

        todo = worker.task_pad.list_todo()
        assert len(todo) == 1
        assert todo[0].content == "检索代码"

    def test_spawn_multiple_workers(self):
        colony = make_test_colony("spawn4")
        cat = colony.create_cat(name="main")

        w1 = cat.spawn_worker("w1", "任务A")
        w2 = cat.spawn_worker("w2", "任务B")
        w3 = cat.spawn_worker("w3", "任务C")

        assert len(colony.list_cats()) == 4  # 1 main + 3 workers
        assert w1.parent_id == cat.cat_uid
        assert w2.parent_id == cat.cat_uid
        assert w3.parent_id == cat.cat_uid

    def test_kitten_event_emitted(self):
        colony = make_test_colony("spawn5")
        cat = colony.create_cat(name="main")

        events = []

        def handler(payload):
            events.append(payload)

        cat.events.on("kitten.spawned", handler)

        cat.spawn_worker("baby", "任务")

        # emit_nowait is synchronous, but we need to give it a moment
        assert len(events) >= 1
        assert events[0]["parent_id"] == cat.cat_uid
        assert "kitten_id" in events[0]
        assert events[0]["task"] == "任务"

    def test_allowed_organs_restriction(self):
        colony = make_test_colony("spawn6")
        cat = colony.create_cat(name="main")

        # 创建受限的 worker
        worker = cat.spawn_worker(
            "restricted",
            "敏感任务",
            allowed_organs=frozenset(
                {"cat_uid", "name", "container", "task_pad"}),
        )

        # 允许的属性应该能访问
        assert worker.cat_uid is not None
        assert worker.name == "restricted"
        assert worker.task_pad is not None

        # 禁用的属性（不在 allowed_organs 中，也不在 _ALWAYS_ALLOWED 中）应抛出异常
        from meowcat.errors import IllegalNeuralPathError
        with pytest.raises(IllegalNeuralPathError):
            _ = worker.host  # host is NOT in _ALWAYS_ALLOWED, not in allowed_organs

    def test_worker_has_own_taskpad_instance(self):
        colony = make_test_colony("spawn7")
        cat = colony.create_cat(name="main")
        cat.task_pad = TaskPad()
        cat.task_pad.post("主猫任务")

        worker = cat.spawn_worker("w", "分身任务")

        # 各自的 TaskPad 独立
        assert cat.task_pad.count() == 1
        assert worker.task_pad.count() == 1
        assert cat.task_pad.list_todo()[0].content == "主猫任务"
        assert worker.task_pad.list_todo()[0].content == "分身任务"
