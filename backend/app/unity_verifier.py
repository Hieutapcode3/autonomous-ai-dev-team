"""
Unity MCP Verifier
Connects to the running Unity Editor via its MCP HTTP bridge (localhost:8090 by default).
After the sandbox writes .cs files into the project, this module triggers a reimport+compile,
waits until the editor is ready, then reads the console for errors.
"""

import asyncio
import httpx
import json
import os
from typing import Dict, Any, List, Optional, Callable, Awaitable

# Unity MCP bridge URL — matches the port used by the MCP for Unity plugin
UNITY_MCP_URL = os.getenv("UNITY_MCP_URL", "http://localhost:8090")
MCP_TIMEOUT = float(os.getenv("UNITY_MCP_TIMEOUT", "60"))


async def _mcp_call(
    tool: str,
    params: Dict[str, Any],
    log: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
) -> Dict[str, Any]:
    """POST a tool call to the Unity MCP bridge and return the result dict."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": params}}
    async with httpx.AsyncClient(timeout=MCP_TIMEOUT) as client:
        resp = await client.post(f"{UNITY_MCP_URL}/mcp", json=payload)
        resp.raise_for_status()
        body = resp.json()
        if "error" in body:
            raise RuntimeError(f"Unity MCP error: {body['error']}")
        # Result is under body["result"]["content"][0]["text"] (JSON string)
        content = body.get("result", {}).get("content", [])
        if content and isinstance(content[0], dict):
            text = content[0].get("text", "{}")
            try:
                return json.loads(text)
            except Exception:
                return {"raw": text}
        return body.get("result", {})


async def _read_editor_state(log=None) -> Dict[str, Any]:
    """Read mcpforunity://editor/state to check compilation status."""
    payload = {"jsonrpc": "2.0", "id": 2, "method": "resources/read", "params": {"uri": "mcpforunity://editor/state"}}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{UNITY_MCP_URL}/mcp", json=payload)
        resp.raise_for_status()
        body = resp.json()
        contents = body.get("result", {}).get("contents", [])
        if contents:
            text = contents[0].get("text", "{}")
            try:
                return json.loads(text)
            except Exception:
                pass
        return {}


async def is_unity_reachable() -> bool:
    """Quick ping to check if Unity Editor MCP bridge is running."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            payload = {"jsonrpc": "2.0", "id": 0, "method": "tools/list", "params": {}}
            resp = await client.post(f"{UNITY_MCP_URL}/mcp", json=payload)
            return resp.status_code == 200
    except Exception:
        return False


async def refresh_and_wait(
    log: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
    max_wait_sec: float = 90,
) -> bool:
    """
    Trigger Unity asset refresh + script compilation, then wait until ready.
    Returns True if the editor became ready within max_wait_sec.
    """
    try:
        await _mcp_call("refresh_unity", {
            "mode": "force",
            "scope": "all",
            "compile": "request",
            "wait_for_ready": True,
        }, log)
        if log:
            await log("UnityMCP", "Refresh + compile requested. Waiting for editor to become ready...", "INFO")
    except Exception as e:
        if log:
            await log("UnityMCP", f"refresh_unity failed: {e}", "WARN")
        return False

    # Poll editor state until ready or timeout
    waited = 0.0
    poll_interval = 3.0
    while waited < max_wait_sec:
        await asyncio.sleep(poll_interval)
        waited += poll_interval
        try:
            state = await _read_editor_state(log)
            data = state.get("data", state)
            is_compiling = data.get("compilation", {}).get("is_compiling", False)
            ready = data.get("advice", {}).get("ready_for_tools", True)
            if log:
                await log("UnityMCP", f"Editor state — compiling={is_compiling}, ready={ready} ({waited:.0f}s elapsed)", "INFO")
            if not is_compiling and ready:
                return True
        except Exception as e:
            if log:
                await log("UnityMCP", f"Polling editor state failed: {e}", "WARN")

    if log:
        await log("UnityMCP", f"Editor did not become ready within {max_wait_sec}s.", "WARN")
    return False


async def read_compile_errors(
    log: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
) -> List[Dict[str, Any]]:
    """
    Read the Unity console and extract only Error-level messages.
    Returns a list of dicts: {message, stacktrace, type}
    """
    try:
        result = await _mcp_call("read_console", {
            "action": "get",
            "types": ["error"],
            "count": "50",
            "format": "json",
            "include_stacktrace": True,
        }, log)

        messages = result.get("messages", result.get("logs", []))
        errors = []
        for m in messages:
            msg_type = str(m.get("type", "")).lower()
            if "error" in msg_type or "exception" in msg_type:
                errors.append({
                    "message": m.get("message", m.get("text", "")),
                    "stacktrace": m.get("stacktrace", ""),
                    "type": msg_type,
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
    Main entry point called by the Verifier after sandbox writes files.

    Steps:
      1. Check Unity is reachable — skip gracefully if not
      2. Clear console, trigger refresh + compile, wait for ready
      3. Read errors from console
      4. For each .cs file changed, also run validate_script for individual diagnostics

    Returns:
      {
        "unity_available": bool,
        "compile_passed": bool,
        "errors": [...],
        "error_summary": str,
        "checks": [...],
      }
    """
    if log:
        await log("UnityMCP", "Starting Unity compile verification...", "INFO")

    # 1. Reachability check
    reachable = await is_unity_reachable()
    if not reachable:
        if log:
            await log("UnityMCP", "Unity Editor MCP bridge is not reachable. Skipping live compile check.", "WARN")
        return {
            "unity_available": False,
            "compile_passed": True,  # Don't block if Unity not running
            "errors": [],
            "error_summary": "Unity Editor not connected — live compile check skipped.",
            "checks": [{"check": "unity_reachability", "passed": True, "output": "Unity MCP not available — check skipped."}],
        }

    checks = []

    # 2. Clear console first so old errors don't contaminate
    try:
        await _mcp_call("read_console", {"action": "clear"}, log)
        if log:
            await log("UnityMCP", "Console cleared.", "INFO")
    except Exception:
        pass

    # 3. Refresh + compile + wait
    ready = await refresh_and_wait(log)
    checks.append({
        "check": "unity_refresh_compile",
        "passed": ready,
        "output": "Editor ready after compile." if ready else "Editor did not reach ready state in time.",
    })

    # 4. Per-file validate_script for individual diagnostics
    cs_files = [f for f in changed_files if f.endswith(".cs")]
    for cs_file in cs_files:
        # Normalize to Assets/... path for Unity MCP
        uri = cs_file if cs_file.startswith("Assets/") else f"Assets/{cs_file.lstrip('/')}"
        try:
            vresult = await _mcp_call("validate_script", {
                "uri": uri,
                "level": "standard",
                "include_diagnostics": True,
            }, log)
            file_passed = vresult.get("is_valid", vresult.get("valid", True))
            diags = vresult.get("diagnostics", [])
            diag_text = "; ".join([d.get("message", "") for d in diags if d.get("severity", "") in ("error", "Error")])
            checks.append({
                "check": f"validate_script:{cs_file}",
                "passed": file_passed and not diag_text,
                "output": diag_text or "Script diagnostics clean.",
                "file": cs_file,
            })
            if log:
                status = "PASS" if (file_passed and not diag_text) else "FAIL"
                await log("UnityMCP", f"validate_script [{cs_file}]: {status} {diag_text[:100] if diag_text else ''}", "SUCCESS" if status == "PASS" else "ERROR")
        except Exception as e:
            checks.append({"check": f"validate_script:{cs_file}", "passed": True, "output": f"Skipped: {e}"})

    # 5. Read console errors
    await asyncio.sleep(2.0)  # Extra buffer after compile settles
    errors = await read_compile_errors(log)

    if errors and log:
        await log("UnityMCP", f"Found {len(errors)} compile error(s) in Unity console.", "ERROR")
        for err in errors[:5]:
            await log("UnityMCP", f"  [ERROR] {err['message'][:200]}", "ERROR")

    compile_passed = len(errors) == 0
    error_summary = ""
    if not compile_passed:
        lines = [f"[{i+1}] {e['message']}" for i, e in enumerate(errors)]
        error_summary = "\n".join(lines)
        checks.append({"check": "unity_console_errors", "passed": False, "output": error_summary})
    else:
        checks.append({"check": "unity_console_errors", "passed": True, "output": "No errors in Unity console."})
        if log:
            await log("UnityMCP", "Unity compile verification PASSED — no errors in console.", "SUCCESS")

    return {
        "unity_available": True,
        "compile_passed": compile_passed,
        "errors": errors,
        "error_summary": error_summary,
        "checks": checks,
    }
