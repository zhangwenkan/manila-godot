"""Send a saved operation to the verified GUI Blender through the installed MCP server.

This process only transports code. Blender evaluates it via execute_blender_code.
"""
import argparse
import asyncio
from datetime import timedelta
import json
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    p = argparse.ArgumentParser()
    p.add_argument('--pid', required=True, type=int)
    p.add_argument('--file', required=True)
    p.add_argument('--code', required=True)
    p.add_argument('--report', required=True)
    p.add_argument('--port', default=9879, type=int)
    p.add_argument('--user-prompt', default='')
    a = p.parse_args()
    code = Path(a.code).read_text(encoding='utf-8-sig')
    guard = (
        'import bpy, os\nfrom pathlib import Path\n'
        f'assert os.getpid() == {a.pid}, "Wrong Blender PID"\n'
        f'assert Path(bpy.data.filepath).resolve() == Path({a.file!r}).resolve(), "Wrong Blender file"\n'
        f'assert bpy.types.blendermcp_server.port == {a.port}, "Wrong Blender port"\n'
    )
    env = dict(os.environ, BLENDER_HOST='127.0.0.1', BLENDER_PORT=str(a.port),
               DISABLE_TELEMETRY='true', BLENDERMCP_NO_UPDATE_CHECK='1', PYTHONUTF8='1')
    exe = Path(os.environ['LOCALAPPDATA']) / 'ManilaBlenderMCP/venv/Scripts/mcp-for-blender.exe'
    async with stdio_client(StdioServerParameters(command=str(exe), args=[], env=env)) as streams:
        async with ClientSession(*streams, read_timeout_seconds=timedelta(seconds=240)) as session:
            await session.initialize()
            arguments = {'code': guard + code}
            if a.user_prompt:
                arguments['user_prompt'] = a.user_prompt
            result = await session.call_tool('execute_blender_code', arguments)
            data = result.model_dump(mode='json')
            Path(a.report).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            output = '\n'.join(x.text for x in result.content if hasattr(x, 'text'))
            print(output)
            if result.isError or 'Traceback' in output or 'Error executing' in output:
                raise SystemExit(1)


if __name__ == '__main__':
    asyncio.run(main())
