"""Local client for the running Blender-MCP addon; never sends to a remote host."""
import argparse
import json
import pathlib
import socket


def request(kind, params, timeout=90):
    with socket.create_connection(("127.0.0.1", 9877), timeout=5) as connection:
        connection.settimeout(timeout)
        connection.sendall(json.dumps({"type": kind, "params": params}).encode("utf-8"))
        buffer = b""
        while True:
            chunk = connection.recv(65536)
            if not chunk:
                raise RuntimeError("Blender closed the connection before a complete response")
            buffer += chunk
            if len(buffer) > 16 * 1024 * 1024:
                raise RuntimeError("Unexpectedly large MCP response")
            try:
                response = json.loads(buffer.decode("utf-8"))
                break
            except (ValueError, UnicodeDecodeError):
                continue
    if response.get("status") != "success":
        raise RuntimeError(json.dumps(response, ensure_ascii=True))
    return response["result"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("script", nargs="?")
    parser.add_argument("--scene", action="store_true")
    parser.add_argument("--screenshot")
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()
    if args.scene:
        result = request("get_scene_info", {}, args.timeout)
    elif args.screenshot:
        path = pathlib.Path(args.screenshot).resolve()
        if path.exists():
            raise SystemExit("Refusing to overwrite a screenshot")
        result = request("get_viewport_screenshot", {"filepath": str(path), "max_size": 1400, "format": "png"}, args.timeout)
    else:
        script = pathlib.Path(args.script).resolve()
        code = script.read_text(encoding="utf-8")
        code = "__file__ = " + repr(str(script)) + "\n" + code
        result = request("execute_code", {"code": code}, args.timeout)
    print(json.dumps(result, ensure_ascii=True, indent=2))
