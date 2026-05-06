# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT

"""meowcat plus MCP Client — multi-protocol tool client framework.

Connects to MCP (Model Context Protocol) servers via stdio or HTTP transport,
discovers their tools, and calls them. Zero external MCP SDK dependency —
pure JSON-RPC 2.0 over subprocess / HTTP.

Usage::

    from meowcat.plus.mcp_client import MCPClient, MCPServerConfig

    mcp = MCPClient()
    mcp.add_server(MCPServerConfig(name="mysql", transport="stdio",
                                   command="mysql-mcp-server"))
    tools = await mcp.discover("mysql")
    result = await mcp.call_tool("mysql", "query", {"sql": "SELECT 1"})
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

from meowcat.constants import MCP_DEFAULT_TIMEOUT  # noqa: E402


@dataclass
class MCPServerConfig:
    """MCP server connection configuration.

    Attributes:
        name: Unique server identifier within this client
        transport: Transport type — ``"stdio"`` (subprocess) or ``"http"``
        command: Executable command for stdio transport
        args: Arguments passed to the command
        url: HTTP endpoint URL for http transport
        enabled: Whether this server is active
    """
    name: str
    transport: str = "stdio"
    command: str = ""
    args: list[str] = field(default_factory=list)
    url: str = ""
    enabled: bool = True


@dataclass
class MCPTool:
    """MCP tool descriptor discovered from a server.

    Attributes:
        name: Tool name
        description: Human-readable description
        parameters: JSON Schema for tool input (from ``inputSchema``)
        server_name: Owning server name
    """
    name: str
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    server_name: str = ""


class MCPClient:
    """MCP multi-server client.

    Manages connections to multiple MCP servers, discovers their tool
    inventories, and calls tools via JSON-RPC 2.0.

    Implements the ``diagnose()`` interface for :class:`meowcat.diagnose.Stethoscope`
    compatibility.
    """

    def __init__(self) -> None:
        self._servers: dict[str, MCPServerConfig] = {}
        self._tools: dict[str, MCPTool] = {}

    # -- Diagnosable interface ---------------------------------------

    def diagnose(self) -> dict[str, Any]:
        """Read-only snapshot for Stethoscope probing.

        Returns:
            ``{"servers": N, "tools": N}``
        """
        return {"servers": len(self._servers), "tools": len(self._tools)}

    # -- Server management -------------------------------------------

    def add_server(self, config: MCPServerConfig) -> None:
        """Register an MCP server."""
        self._servers[config.name] = config

    def remove_server(self, name: str) -> None:
        """Unregister an MCP server and clear its tools."""
        self._servers.pop(name, None)
        self._tools = {
            k: v for k, v in self._tools.items() if v.server_name != name
        }

    def list_servers(self) -> list[MCPServerConfig]:
        """List all registered servers."""
        return list(self._servers.values())

    def list_tools(self, server_name: str = "") -> list[MCPTool]:
        """List discovered tools, optionally filtered by server."""
        if server_name:
            return [t for t in self._tools.values()
                    if t.server_name == server_name]
        return list(self._tools.values())

    # -- Discovery ---------------------------------------------------

    async def discover(self, server_name: str) -> list[MCPTool]:
        """Connect to an MCP server and discover its tools.

        For stdio transport, spawns the server subprocess, sends an
        ``initialize`` handshake followed by ``tools/list``.
        """
        cfg = self._servers.get(server_name)
        if not cfg:
            logger.warning("Server '%s' not configured", server_name)
            return []

        if cfg.transport == "stdio":
            return await self._discover_stdio(cfg)
        return await self._discover_http(cfg)

    # -- Tool calling ------------------------------------------------

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> str:
        """Call a tool on an MCP server.

        Returns the tool's result as a string.
        """
        cfg = self._servers.get(server_name)
        if not cfg:
            return f"MCP server '{server_name}' not found"

        if cfg.transport == "stdio":
            return await self._call_tool_stdio(cfg, tool_name, arguments)
        return await self._call_tool_http(cfg, tool_name, arguments)
# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT


    # -- Stdio transport internals -----------------------------------

    async def _discover_stdio(self, cfg: MCPServerConfig) -> list[MCPTool]:
        try:
            proc = await asyncio.create_subprocess_exec(
                cfg.command, *cfg.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError:
            logger.error("MCP command not found: %s", cfg.command)
            return []
        except Exception as e:
            logger.error("MCP spawn error: %s", e)
            return []

        try:
            if proc.stdin is None or proc.stdout is None:
                logger.error("MCP process has no stdio pipes")
                return []

            # Send initialize handshake
            req = _jsonrpc_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "MeowCat", "version": "1.0"},
            })
            proc.stdin.write((req + "\n").encode())
            await proc.stdin.drain()

            line = await asyncio.wait_for(proc.stdout.readline(), timeout=10.0)
            if not line:
                logger.error("MCP init: empty response")
                return []
            resp = json.loads(line.decode())
            if "error" in resp:
                logger.error("MCP init error: %s", resp["error"])
                return []
# Copyright (c) 2026 Axonant
# SPDX-License-Identifier: MIT


            # Send tools/list on the same session
            req2 = _jsonrpc_request("tools/list", {})
            proc.stdin.write((req2 + "\n").encode())
            await proc.stdin.drain()

            line2 = await asyncio.wait_for(proc.stdout.readline(), timeout=10.0)
            resp2 = json.loads(line2.decode())
            tools_data = resp2.get("result", {}).get("tools", [])
            tools: list[MCPTool] = []
            for td in tools_data:
                tool = MCPTool(
                    name=td.get("name", ""),
                    description=td.get("description", ""),
                    parameters=td.get("inputSchema", {}),
                    server_name=cfg.name,
                )
                self._tools[f"{cfg.name}:{tool.name}"] = tool
                tools.append(tool)
            return tools
        except asyncio.TimeoutError:
            logger.error("MCP discovery timed out: %s", cfg.name)
            return []
        except Exception as e:
            logger.error("MCP discovery error: %s", e)
            return []
        finally:
            try:
                proc.terminate()
            except Exception:
                logger.debug("MCP process termination error", exc_info=True)

    async def _call_tool_stdio(
        self, cfg: MCPServerConfig, tool_name: str,
        arguments: dict[str, Any],
    ) -> str:
        try:
            proc = await asyncio.create_subprocess_exec(
                cfg.command, *cfg.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            req = _jsonrpc_request(
                "tools/call", {"name": tool_name, "arguments": arguments})
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=req.encode()), timeout=MCP_DEFAULT_TIMEOUT,
            )
            if proc.returncode != 0:
                return f"MCP error: {stderr.decode()[:500]}"
            resp = json.loads(stdout.decode())
            if "error" in resp:
                return f"MCP error: {resp['error'].get('message', resp['error'])}"
            result = resp.get("result", {})
            content = result.get("content", [])
            if isinstance(content, list) and content:
                texts = [
                    c.get("text", "") for c in content
                    if isinstance(c, dict)
                ]
                return "\n".join(texts) if texts else json.dumps(result)
            return json.dumps(result)
        except asyncio.TimeoutError:
            return "MCP call timed out"
        except Exception as e:
            return f"MCP call error: {e}"

    # -- HTTP transport internals ------------------------------------

    async def _discover_http(self, cfg: MCPServerConfig) -> list[MCPTool]:
        """Discover tools via HTTP transport (JSON-RPC 2.0 over HTTP POST)."""
        try:
            import httpx
        except ImportError:
            logger.error("httpx not installed. Run: pip install httpx")
            return []

        try:
            async with httpx.AsyncClient(timeout=MCP_DEFAULT_TIMEOUT) as client:
                init_req = _jsonrpc_request("initialize", {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "MeowCat", "version": "1.0"},
                })
                init_resp = await client.post(
                    cfg.url,
                    json=json.loads(init_req),
                    headers={"Content-Type": "application/json"},
                )
                init_resp.raise_for_status()
                init_data = init_resp.json()
                if "error" in init_data:
                    logger.error("MCP init error: %s", init_data["error"])
                    return []

                list_req = _jsonrpc_request("tools/list", {})
                list_resp = await client.post(
                    cfg.url,
                    json=json.loads(list_req),
                    headers={"Content-Type": "application/json"},
                )
                list_resp.raise_for_status()
                list_data = list_resp.json()
                if "error" in list_data:
                    logger.error("MCP tools/list error: %s",
                                 list_data["error"])
                    return []

                tools_data = list_data.get("result", {}).get("tools", [])
                tools: list[MCPTool] = []
                for td in tools_data:
                    tool = MCPTool(
                        name=td.get("name", ""),
                        description=td.get("description", ""),
                        parameters=td.get("inputSchema", {}),
                        server_name=cfg.name,
                    )
                    self._tools[f"{cfg.name}:{tool.name}"] = tool
                    tools.append(tool)
                return tools
        except Exception as e:
            logger.error("MCP HTTP discovery error: %s", e)
            return []

    async def _call_tool_http(
        self, cfg: MCPServerConfig, tool_name: str,
        arguments: dict[str, Any],
    ) -> str:
        try:
            import httpx
        except ImportError:
            return "httpx not installed. Run: pip install httpx"

        try:
            req = _jsonrpc_request(
                "tools/call", {"name": tool_name, "arguments": arguments})
            async with httpx.AsyncClient(timeout=MCP_DEFAULT_TIMEOUT) as client:
                resp = await client.post(
                    cfg.url,
                    json=json.loads(req),
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()
                if "error" in data:
                    return f"MCP error: {data['error'].get('message', data['error'])}"
                return json.dumps(data.get("result", {}))
        except Exception as e:
            return f"MCP HTTP call error: {e}"


def _jsonrpc_request(method: str, params: dict[str, Any]) -> str:
    """Build a JSON-RPC 2.0 request string."""
    return json.dumps({
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1,
    })

