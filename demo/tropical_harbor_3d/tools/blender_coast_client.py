"""Transport only: invoke the installed Blender MCP against the isolated harbor session."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ROOT / 'source' / 'harbor_coast_mcp.blend'


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['list', 'info', 'execute', 'screenshot'])
    parser.add_argument('--payload', type=Path)
    parser.add_argument('--pid', type=int, required=True)
    args = parser.parse_args()
    env = dict(os.environ)
    env.pop('PYTHONHOME', None)
    env.pop('PYTHONPATH', None)
    env['BLENDER_HOST'] = '127.0.0.1'
    env['BLENDER_PORT'] = '9878'
    server = StdioServerParameters(command='D:/一些好玩的例子/blender-mcp/.venv/Scripts/python.exe',
                                  args=['-m', 'blender_mcp.server'], env=env)
    async with stdio_client(server) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            if args.action == 'list':
                result = await session.list_tools()
                print(json.dumps([{'name': t.name, 'schema': t.inputSchema} for t in result.tools], ensure_ascii=False))
                return
            guard = ('import bpy, os\nfrom pathlib import Path\n'
                     f'assert os.getpid() == {args.pid}, "Unexpected Blender process"\n'
                     f'assert Path(bpy.data.filepath).resolve() == Path({str(EXPECTED)!r}).resolve(), "Unexpected Blender file"\n')
            if args.action == 'info':
                code = guard + 'print({"pid":os.getpid(),"file":bpy.data.filepath,"collections":[(c.name,len(c.objects)) for c in bpy.data.collections],"materials":[m.name for m in bpy.data.materials]})'
            else:
                payload = json.loads(args.payload.read_text(encoding='utf-8'))
                code = guard + payload['code']
            result = await session.call_tool('execute_blender_code', {'code': code})
            for item in result.content:
                if item.type == 'text':
                    print(item.text)
            if result.isError or any('Error executing code:' in getattr(item, 'text', '') for item in result.content):
                raise SystemExit(2)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(main())
