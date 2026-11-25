"""Exercise the stdio MCP connection and read only from the expected Blender PID."""
import argparse
import asyncio
from datetime import timedelta
import json
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--port', type=int, default=9879)
    parser.add_argument('--file', default='')
    parser.add_argument('--report', required=True)
    parser.add_argument('--close', action='store_true')
    args = parser.parse_args()
    env = dict(os.environ, BLENDER_HOST='127.0.0.1', BLENDER_PORT=str(args.port),
               DISABLE_TELEMETRY='true', BLENDERMCP_NO_UPDATE_CHECK='1')
    command = Path(os.environ['LOCALAPPDATA']) / 'ManilaBlenderMCP/venv/Scripts/mcp-for-blender.exe'
    report = {'expected_pid': args.pid, 'expected_file': args.file, 'port': args.port}
    async with stdio_client(StdioServerParameters(command=str(command), args=[], env=env)) as streams:
        async with ClientSession(*streams, read_timeout_seconds=timedelta(seconds=120)) as session:
            info = await session.initialize()
            report['server'] = info.serverInfo.model_dump()
            listed = await session.list_tools()
            report['tools'] = [tool.name for tool in listed.tools]
            assert 'execute_blender_code' in report['tools']
            code = (
                'import bpy, os, json\n'
                'from pathlib import Path\n'
                f'assert os.getpid() == {args.pid}, "Wrong Blender process"\n'
                f'expected = {args.file!r}\n'
                'assert (Path(bpy.data.filepath).resolve() == Path(expected).resolve()) if expected else not bpy.data.filepath\n'
                'print(json.dumps({"pid": os.getpid(), "file": bpy.data.filepath, '
                '"blender": bpy.app.version_string, "objects": len(bpy.data.objects), '
                '"dirty": bpy.data.is_dirty, "port": bpy.types.blendermcp_server.port, '
                '"host": bpy.types.blendermcp_server.host}))\n'
            )
            result = await session.call_tool('execute_blender_code', {'code': code})
            assert not result.isError, result
            text = '\n'.join(item.text for item in result.content if hasattr(item, 'text'))
            assert 'Traceback' not in text and 'Error executing' not in text, text
            assert str(args.pid) in text, text
            report['read_only_check'] = text
            report['passed'] = True
            Path(args.report).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
            print(json.dumps(report, indent=2, ensure_ascii=False))
            if args.close:
                result = await session.call_tool('execute_blender_code', {'code':
                    f'import os, bpy\nassert os.getpid() == {args.pid}\n'
                    'def quit_verified_process():\n    bpy.ops.wm.quit_blender()\n    return None\n'
                    'bpy.app.timers.register(quit_verified_process, first_interval=1.0)\n'
                    'print("Verified session scheduled to close without saving")\n'})
                assert not result.isError, result


if __name__ == '__main__':
    asyncio.run(main())
