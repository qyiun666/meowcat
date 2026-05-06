# Copyright (c) 2026 qyiun666
# SPDX-License-Identifier: MIT

"""meowcat v1.1.14 — MCP Client 多协议工具客户端 测试。

覆盖:
- MCPServerConfig / MCPTool 数据类创建
- MCPClient 服务器管理（add/remove/list）
- MCPClient 工具管理（list_tools）
- diagnose() 听诊器接口
- _jsonrpc_request JSON-RPC 请求构建
- discover 无配置服务器返回空
- call_tool 无配置服务器返回错误
- call_tool stdio 子进程模拟（echo 服务端）
- 独立测试（零 CatBase/Colony 依赖）
"""

from __future__ import annotations

import json

import pytest

from meowcat import MCPClient, MCPServerConfig, MCPTool
from meowcat.plus.mcp_client import _jsonrpc_request


# -- 1. MCPServerConfig 数据类 ---------------------------------------

class TestMCPServerConfig:
    """MCPServerConfig 创建与默认值。"""

    def test_minimal(self) -> None:
        cfg = MCPServerConfig(name="test")
        assert cfg.name == "test"
        assert cfg.transport == "stdio"
        assert cfg.command == ""
        assert cfg.args == []
        assert cfg.url == ""
        assert cfg.enabled is True

    def test_stdio_full(self) -> None:
        cfg = MCPServerConfig(
            name="mysql",
            transport="stdio",
            command="mysql-mcp-server",
            args=["--port", "8080"],
        )
        assert cfg.name == "mysql"
        assert cfg.transport == "stdio"
        assert cfg.command == "mysql-mcp-server"
        assert cfg.args == ["--port", "8080"]

    def test_http_full(self) -> None:
        cfg = MCPServerConfig(
            name="remote",
            transport="http",
            url="http://localhost:9000/mcp",
            enabled=False,
        )
        assert cfg.name == "remote"
        assert cfg.transport == "http"
        assert cfg.url == "http://localhost:9000/mcp"
        assert cfg.enabled is False


# -- 2. MCPTool 数据类 -----------------------------------------------

class TestMCPTool:
    """MCPTool 创建与默认值。"""

    def test_minimal(self) -> None:
        tool = MCPTool(name="query")
        assert tool.name == "query"
        assert tool.description == ""
        assert tool.parameters == {}
        assert tool.server_name == ""

    def test_full(self) -> None:
        tool = MCPTool(
            name="query",
            description="Execute SQL query",
            parameters={"type": "object", "properties": {}},
            server_name="mysql",
        )
        assert tool.name == "query"
        assert tool.description == "Execute SQL query"
        assert tool.parameters == {"type": "object", "properties": {}}
        assert tool.server_name == "mysql"


# -- 3. MCPClient 服务器管理 -----------------------------------------

class TestServerManagement:
    """MCPClient add_server / remove_server / list_servers。"""

    def test_add_and_list(self) -> None:
        client = MCPClient()
        client.add_server(MCPServerConfig(name="a"))
        client.add_server(MCPServerConfig(name="b"))
        servers = client.list_servers()
        assert len(servers) == 2
        names = {s.name for s in servers}
        assert names == {"a", "b"}

    def test_remove_server(self) -> None:
        client = MCPClient()
        client.add_server(MCPServerConfig(name="a"))
        client.add_server(MCPServerConfig(name="b"))
        client.remove_server("a")
        assert len(client.list_servers()) == 1
        assert client.list_servers()[0].name == "b"

    def test_remove_nonexistent(self) -> None:
        client = MCPClient()
        client.remove_server("nonexistent")  # no error

    def test_remove_clears_tools(self) -> None:
        client = MCPClient()
        client.add_server(MCPServerConfig(name="srv"))
        # Manually inject a tool for testing cleanup
        client._tools["srv:t1"] = MCPTool(name="t1", server_name="srv")
        client.remove_server("srv")
        assert client.list_tools() == []


# -- 4. MCPClient 工具管理 -------------------------------------------

class TestToolListing:
    """MCPClient list_tools。"""

    def test_empty(self) -> None:
        client = MCPClient()
        assert client.list_tools() == []

    def test_filter_by_server(self) -> None:
        client = MCPClient()
        client._tools["a:t1"] = MCPTool(name="t1", server_name="a")
        client._tools["b:t2"] = MCPTool(name="t2", server_name="b")
        assert len(client.list_tools("a")) == 1
        assert client.list_tools("a")[0].server_name == "a"
        assert len(client.list_tools("b")) == 1

    def test_all_tools(self) -> None:
        client = MCPClient()
        client._tools["a:t1"] = MCPTool(name="t1", server_name="a")
        client._tools["a:t2"] = MCPTool(name="t2", server_name="a")
        assert len(client.list_tools()) == 2


# -- 5. diagnose() 听诊器接口 ----------------------------------------

class TestDiagnose:
    """MCPClient.diagnose() 只读快照。"""

    def test_empty(self) -> None:
        client = MCPClient()
        diag = client.diagnose()
        assert diag == {"servers": 0, "tools": 0}

    def test_with_data(self) -> None:
        client = MCPClient()
        client.add_server(MCPServerConfig(name="a"))
        client._tools["a:t1"] = MCPTool(name="t1", server_name="a")
        diag = client.diagnose()
        assert diag["servers"] == 1
        assert diag["tools"] == 1


# -- 6. JSON-RPC 请求构建 --------------------------------------------

class TestJsonRpcRequest:
    """_jsonrpc_request 辅助函数。"""

    def test_initialize(self) -> None:
        req = _jsonrpc_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "MeowCat", "version": "1.0"},
        })
        data = json.loads(req)
        assert data["jsonrpc"] == "2.0"
        assert data["method"] == "initialize"
        assert data["id"] == 1
        assert data["params"]["protocolVersion"] == "2024-11-05"

    def test_tools_list(self) -> None:
        req = _jsonrpc_request("tools/list", {})
        data = json.loads(req)
        assert data["method"] == "tools/list"
        assert data["params"] == {}

    def test_tools_call(self) -> None:
        req = _jsonrpc_request(
            "tools/call", {"name": "query", "arguments": {"sql": "SELECT 1"}})
        data = json.loads(req)
        assert data["method"] == "tools/call"
        assert data["params"]["name"] == "query"
        assert data["params"]["arguments"] == {"sql": "SELECT 1"}


# -- 7. discover / call_tool 无配置服务器 ----------------------------

class TestMissingServer:
    """discover / call_tool 对未配置服务器的处理。"""

    @pytest.mark.asyncio
    async def test_discover_missing_server(self) -> None:
        client = MCPClient()
        tools = await client.discover("nonexistent")
        assert tools == []

    @pytest.mark.asyncio
    async def test_call_tool_missing_server(self) -> None:
        client = MCPClient()
        result = await client.call_tool("nonexistent", "tool", {})
        assert result == "MCP server 'nonexistent' not found"


# -- 8. call_tool stdio 子进程模拟 -----------------------------------

class TestCallToolStdioMock:
    """使用 echo 脚本模拟 MCP 调用。"""

    @pytest.mark.asyncio
    async def test_call_tool_stdio_echo(self) -> None:
        """用 Python echo 子进程模拟 MCP tools/call 响应。"""
        import sys

        # 构造一个最小 echo 脚本：读取 stdin JSON-RPC，返回固定 mock 响应
        echo_script = (
            "import sys, json\n"
            "req = json.loads(sys.stdin.read())\n"
            "result = {'content': [{'type': 'text', "
            "'text': f'called {req[\"params\"][\"name\"]}'}]}\n"
            "json.dump({'jsonrpc': '2.0', 'result': result, 'id': 1}, sys.stdout)\n"
        )
        client = MCPClient()
        client.add_server(MCPServerConfig(
            name="echo",
            transport="stdio",
            command=sys.executable,
            args=["-c", echo_script],
        ))
        result = await client.call_tool("echo", "my_tool", {"x": 1})
        assert "called my_tool" in result

    @pytest.mark.asyncio
    async def test_call_tool_stdio_error(self) -> None:
        """子进程返回 JSON-RPC error 时的处理。"""
        import sys

        error_script = (
            "import sys, json\n"
            "json.dump({'jsonrpc': '2.0', "
            "'error': {'code': -32601, 'message': 'Tool not found'}, "
            "'id': 1}, sys.stdout)\n"
        )
        client = MCPClient()
        client.add_server(MCPServerConfig(
            name="err",
            transport="stdio",
            command=sys.executable,
            args=["-c", error_script],
        ))
        result = await client.call_tool("err", "bad_tool", {})
        assert "Tool not found" in result

    @pytest.mark.asyncio
    async def test_call_tool_stdio_nonzero_exit(self) -> None:
        """子进程非零退出时的错误处理。"""
        import sys

        fail_script = (
            "import sys\n"
            "sys.stderr.write('something crashed')\n"
            "sys.exit(1)\n"
        )
        client = MCPClient()
        client.add_server(MCPServerConfig(
            name="fail",
            transport="stdio",
            command=sys.executable,
            args=["-c", fail_script],
        ))
        result = await client.call_tool("fail", "tool", {})
        assert "MCP error:" in result


# -- 9. discover stdio 子进程模拟 ------------------------------------

class TestDiscoverStdioMock:
    """使用 echo 脚本模拟 MCP 工具发现。"""

    @pytest.mark.asyncio
    async def test_discover_stdio(self) -> None:
        """模拟 MCP initialize + tools/list 单进程返回工具列表。"""
        import sys

        counter_script = (
            "import sys, json\n"
            "for line in sys.stdin:\n"
            "    req = json.loads(line)\n"
            "    method = req['method']\n"
            "    if method == 'initialize':\n"
            "        resp = {'jsonrpc': '2.0', 'result': {'protocolVersion': '2024-11-05'}, 'id': 1}\n"
            "    elif method == 'tools/list':\n"
            "        resp = {'jsonrpc': '2.0', 'result': {'tools': ["
            "{'name': 't1', 'description': 'T1', 'inputSchema': {}},"
            "{'name': 't2', 'description': 'T2', 'inputSchema': {}}"
            "]}, 'id': 1}\n"
            "    else:\n"
            "        resp = {'jsonrpc': '2.0', 'error': {'message': 'bad'}, 'id': 1}\n"
            "    sys.stdout.write(json.dumps(resp) + '\\n')\n"
            "    sys.stdout.flush()\n"
        )

        client = MCPClient()
        client.add_server(MCPServerConfig(
            name="test",
            transport="stdio",
            command=sys.executable,
            args=["-c", counter_script],
        ))
        tools = await client.discover("test")
        assert len(tools) == 2
        assert tools[0].name == "t1"
        assert tools[1].name == "t2"
        assert tools[0].server_name == "test"

    @pytest.mark.asyncio
    async def test_discover_command_not_found(self) -> None:
        """命令不存在的错误处理。"""
        client = MCPClient()
        client.add_server(MCPServerConfig(
            name="missing",
            transport="stdio",
            command="/nonexistent/path/to/binary",
        ))
        tools = await client.discover("missing")
        assert tools == []


# -- 10. 独立测试 -----------------------------------------------------

class TestStandalone:
    """MCPClient 完全独立，零依赖 CatBase/Colony。"""

    def test_no_dependency_on_cat(self) -> None:
        from meowcat.plus.mcp_client import MCPClient as DirectClient
        client = DirectClient()
        assert client.diagnose() == {"servers": 0, "tools": 0}

    def test_from_meowcat_top_level(self) -> None:
        client = MCPClient()
        cfg = MCPServerConfig(name="x")
        client.add_server(cfg)
        assert len(client.list_servers()) == 1

