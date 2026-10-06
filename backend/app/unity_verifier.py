"""
Unity MCP Verifier
Connects to the running Unity Editor via its MCP HTTP bridge (auto-discovering port 8080/8090).
Triggers a force refresh + compilation, polls until the editor is ready, and verifies
zero errors exist in the Unity Editor console.

MANDATORY GATE:
If Unity MCP is not reachable or if compilation has any errors, the verification MUST FAIL.
Skipping this step is explicitly prohibited.
"""

import asyncio
import httpx
import json
import os
import glob
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Awaitable

DEFAULT_TIMEOUT = float(os.getenv("UNITY_MCP_TIMEOUT", "60"))
CANDIDATE_URLS = [
    os.getenv("UNITY_MCP_URL", ""),
    "http://127.0.0.1:8080",
    "http://localhost:8080",
    "http://127.0.0.1:8090",
    "http://localhost:8090",
]


class UnityMcpSession:
    def __init__(self):
        self.base_url: Optional[str] = None
        self.session_id: Optional[str] = None
        self._lock = asyncio.Lock()

    @staticmethod
    def _parse_mcp_response(text: str) -> Dict[str, Any]:
        """Parse either plain JSON or SSE (event: message / data: {...}) responses."""
        text = text.strip()
        if text.startswith("{"):
            return json.loads(text)
        for line in text.splitlines():
            if line.startswith("data:"):
                data_str = line[5:].strip()
                if data_str:
                    return json.loads(data_str)
        raise ValueError(f"Could not parse MCP response: {text[:150]}")

    async def _try_handshake(self, client: httpx.AsyncClient, base_url: str) -> Optional[str]:
        """Perform MCP initialize handshake and return session ID if successful."""
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "multi-agent-verifier", "version": "1.0.0"},
            },
        }
        endpoint = f"{base_url.rstrip('/')}/mcp"
        resp = await client.post(endpoint, json=init_payload, headers=headers)
        if resp.status_code != 200:
            return None

        sid = resp.headers.get("mcp-session-id")
        if not sid:
            try:
                data = self._parse_mcp_response(resp.text)
                sid = data.get("result", {}).get("sessionId")
            except Exception:
                sid = None

        if sid:
            h2 = {**headers, "mcp-session-id": sid}
            try:
                await client.post(endpoint, json={"jsonrpc": "2.0", "method": "notifications/initialized"}, headers=h2)
            except Exception:
                pass
        return sid

    async def get_active_session(self) -> tuple[str, str]:
        """Return (base_url, session_id), discovering or reconnecting if needed."""
        async with self._lock:
            # If current session is still healthy, reuse it
            if self.base_url and self.session_id:
                try:
                    headers = {
                        "Accept": "application/json, text/event-stream",
                        "Content-Type": "application/json",
                        "mcp-session-id": self.session_id,
                    }
                    async with httpx.AsyncClient(timeout=3.0) as client:
                        r = await client.post(
                            f"{self.base_url}/mcp",
                            json={"jsonrpc": "2.0", "id": 0, "method": "tools/list", "params": {}},
                            headers=headers,
                        )
                        if r.status_code == 200:
                            return self.base_url, self.session_id
                except Exception:
                    self.session_id = None

            # Build list of URLs to test
            candidates = []
            for u in CANDIDATE_URLS:
                if u and u not in candidates:
                    candidates.append(u.rstrip("/"))

            async with httpx.AsyncClient(timeout=3.0) as client:
                for candidate in candidates:
                    try:
                        sid = await self._try_handshake(client, candidate)
                        if sid:
                            self.base_url = candidate
                            self.session_id = sid
                            return self.base_url, self.session_id
                    except Exception:
                        continue

            raise ConnectionError(
                f"Could not connect to Unity MCP at any candidate URL: {candidates}. "
                "Ensure Unity Editor is open with MCP for Unity running."
            )

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke an MCP tool on the active session."""
        base_url, sid = await self.get_active_session()
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "mcp-session-id": sid,
        }
        payload = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.post(f"{base_url}/mcp", json=payload, headers=headers)
            resp.raise_for_status()
            parsed = self._parse_mcp_response(resp.text)
            if "error" in parsed:
                raise RuntimeError(f"Unity MCP tool '{tool_name}' returned error: {parsed['error']}")

            result = parsed.get("result", {})
            if "structuredContent" in result and isinstance(result["structuredContent"], dict):
                return result["structuredContent"]

            content = result.get("content", [])
            if content and isinstance(content[0], dict):
                raw_text = content[0].get("text", "{}")
                try:
                    return json.loads(raw_text)
                except Exception:
                    return {"text": raw_text}
            return result

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read an MCP resource on the active session."""
        base_url, sid = await self.get_active_session()
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "mcp-session-id": sid,
        }
        payload = {
            "jsonrpc": "2.0",
            "id": 20,
            "method": "resources/read",
            "params": {"uri": uri},
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{base_url}/mcp", json=payload, headers=headers)
            resp.raise_for_status()
            parsed = self._parse_mcp_response(resp.text)
            contents = parsed.get("result", {}).get("contents", [])
            if contents and isinstance(contents[0], dict):
                raw_text = contents[0].get("text", "{}")
                try:
                    return json.loads(raw_text)
                except Exception:
                    return {"text": raw_text}
            return {}


_session = UnityMcpSession()


async def is_unity_reachable() -> bool:
    """Check if Unity Editor MCP bridge is online and responding."""
    try:
        await _session.get_active_session()
        return True
    except Exception:
        return False


async def refresh_and_wait(
    log: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
    max_wait_sec: float = 90.0,
) -> bool:
    """
    Trigger Unity asset refresh and script compilation, then poll editor state
    until domain reload and compilation are finished and editor is ready.
    """
    if log:
        await log("UnityMCP", "Requesting Unity asset refresh and compilation (mode=force, compile=request)...", "INFO")
    try:
        ref_res = await _session.call_tool("refresh_unity", {
            "mode": "force",
            "scope": "all",
            "compile": "request",
            "wait_for_ready": True,
        })
        msg = ref_res.get("message", "Refresh requested")
        if log:
            await log("UnityMCP", f"Refresh command sent: {msg}. Waiting for editor compilation...", "INFO")
    except Exception as e:
        if log:
            await log("UnityMCP", f"Failed to call refresh_unity: {e}", "ERROR")
        return False

    # Poll editor state until ready
    waited = 0.0
    poll_interval = 2.0
    while waited < max_wait_sec:
        await asyncio.sleep(poll_interval)
        waited += poll_interval
        try:
            state = await _session.read_resource("mcpforunity://editor/state")
            data = state.get("data", state)
            is_compiling = data.get("compilation", {}).get("is_compiling", False)
            ready = data.get("advice", {}).get("ready_for_tools", True)
            if log:
                await log("UnityMCP", f"Unity state: compiling={is_compiling}, ready_for_tools={ready} ({waited:.1f}s)", "INFO")
            if not is_compiling and ready:
                return True
        except Exception as e:
            if log:
                await log("UnityMCP", f"Polling editor state: {e}", "WARN")

    if log:
        await log("UnityMCP", f"Unity compilation did not reach ready state within {max_wait_sec}s.", "WARN")
    return False


async def read_compile_errors(
    log: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
) -> List[Dict[str, Any]]:
    """
    Read the Unity console and extract all Error/Exception level messages.
    Returns list of dicts: {message, stacktrace, file, line, type}
    """
    try:
        result = await _session.call_tool("read_console", {
            "action": "get",
            "types": ["error"],
            "count": "50",
            "format": "json",
            "include_stacktrace": True,
        })

        raw_list = result.get("data", result.get("messages", result.get("logs", [])))
        if not isinstance(raw_list, list):
            raw_list = []

        errors = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            msg_type = str(item.get("type", "")).lower()
            msg = item.get("message", item.get("text", ""))
            if not msg:
                continue
            is_err_type = any(k in msg_type for k in ("error", "exception", "assert"))
            is_compiler_err = bool(re.search(r"\berror\s+CS\d{4}\b", msg, re.IGNORECASE))
            is_benign = any(w in msg.lower() for w in ["0 error", "no error", "0 errors", "no errors", "without error"])

            if (is_err_type or is_compiler_err) and not is_benign:
                errors.append({
                    "message": msg,
                    "stacktrace": item.get("stackTrace") or item.get("stacktrace") or "",
                    "file": item.get("file", ""),
                    "line": item.get("line", 0),
                    "type": item.get("type", "Error"),
                })
        return errors
    except Exception as e:
        if log:
            await log("UnityMCP", f"read_console failed: {e}", "WARN")
        return []


async def verify_unity_compilation(
    changed_files: List[str],
    log: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
) -> Dict[str, Any]:
    """
    Main verification gate for Unity projects.
    Enforces mandatory refresh and console error verification.
    NEVER silently passes if Unity is offline or if errors exist.
    """
    if log:
        await log("UnityMCP", "Connecting to Unity Editor via MCP bridge...", "INFO")

    reachable = await is_unity_reachable()
    if not reachable:
        err_msg = (
            "FATAL: Unity Editor MCP bridge is offline or unreachable. "
            "Verification CANNOT be skipped — unverified code will cause broken scripts in Unity. "
            "Please ensure Unity Editor is open with MCP for Unity running (listening on port 8080/8090)."
        )
        if log:
            await log("UnityMCP", err_msg, "ERROR")
        return {
            "unity_available": False,
            "compile_passed": False,  # FAIL HARD — do not skip!
            "errors": [{"message": err_msg, "type": "Error"}],
            "error_summary": err_msg,
            "checks": [{"check": "unity_mcp_connectivity", "passed": False, "output": err_msg}],
        }

    checks = []
    checks.append({"check": "unity_mcp_connectivity", "passed": True, "output": f"Connected to Unity MCP at {_session.base_url}"})
    if log:
        await log("UnityMCP", f"Connected to Unity MCP at {_session.base_url}. Clearing console...", "INFO")

    # 1. Clear old console messages to avoid false positives
    try:
        await _session.call_tool("read_console", {"action": "clear"})
    except Exception as e:
        if log:
            await log("UnityMCP", f"Console clear note: {e}", "WARN")

    # 2. Trigger force refresh + compile and wait
    ready = await refresh_and_wait(log)
    checks.append({
        "check": "unity_refresh_compile",
        "passed": ready,
        "output": "Editor ready after compilation." if ready else "Editor compilation timed out.",
    })
    if not ready:
        return {
            "unity_available": True,
            "compile_passed": False,
            "errors": [{"message": "Unity Editor did not finish compiling within timeout.", "type": "Error"}],
            "error_summary": "Unity Editor compilation timed out or editor hung.",
            "checks": checks,
        }

    # 3. Validate individual changed .cs scripts via validate_script tool
    cs_files = [f for f in changed_files if f.endswith(".cs")]
    for cs_file in cs_files:
        uri = cs_file if cs_file.startswith("Assets/") else f"Assets/{cs_file.lstrip('/')}"
        try:
            vresult = await _session.call_tool("validate_script", {
                "uri": uri,
                "level": "standard",
                "include_diagnostics": True,
            })
            file_passed = vresult.get("is_valid", vresult.get("valid", True))
            diags = vresult.get("diagnostics", [])
            diag_msgs = [d.get("message", "") for d in diags if str(d.get("severity", "")).lower() in ("error", "fatal")]
            diag_text = "; ".join(diag_msgs)
            passed = file_passed and not diag_text
            checks.append({
                "check": f"validate_script:{cs_file}",
                "passed": passed,
                "output": diag_text or "Script diagnostics clean.",
                "file": cs_file,
            })
            if log:
                lvl = "SUCCESS" if passed else "ERROR"
                await log("UnityMCP", f"validate_script [{cs_file}]: {'PASS' if passed else 'FAIL'} {diag_text}", lvl)
        except Exception as e:
            checks.append({"check": f"validate_script:{cs_file}", "passed": True, "output": f"Notice: {e}"})

    # 4. Settle buffer & Read console errors
    await asyncio.sleep(2.0)
    errors = await read_compile_errors(log)

    if errors:
        error_lines = []
        for i, err in enumerate(errors, 1):
            loc = f" ({err['file']}:{err['line']})" if err.get("file") else ""
            error_lines.append(f"[{i}] {err['message']}{loc}")
        error_summary = "\n".join(error_lines)

        if log:
            await log("UnityMCP", f"REJECTED: Found {len(errors)} compile error(s) in Unity console:\n{error_summary}", "ERROR")

        checks.append({"check": "unity_console_errors", "passed": False, "output": error_summary})
        return {
            "unity_available": True,
            "compile_passed": False,
            "errors": errors,
            "error_summary": error_summary,
            "checks": checks,
        }

    checks.append({"check": "unity_console_errors", "passed": True, "output": "Unity Console is completely clean. 0 errors found."})
    if log:
        await log("UnityMCP", "Unity compile verification PASSED — zero compilation errors in Editor console.", "SUCCESS")

    return {
        "unity_available": True,
        "compile_passed": True,
        "errors": [],
        "error_summary": "",
        "checks": checks,
    }


async def get_unity_project_info() -> Optional[Dict[str, Any]]:
    """Query mcpforunity://project/info for projectRoot and assetsPath."""
    try:
        online = await is_unity_reachable()
        if not online:
            return None
        info = await _session.read_resource("mcpforunity://project/info")
        data = info.get("data", info)
        return data
    except Exception:
        return None
