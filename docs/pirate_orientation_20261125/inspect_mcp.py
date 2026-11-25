"""Read owned GUI session status via MCP, without editing scene data."""
import asyncio, json, os
from pathlib import Path
from datetime import timedelta
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

PROMPT = '位置按照你的方案推进，我觉得海盗岛可以转更多的角度，看起来更背对画面一些，当发生海盗劫持时，再把镜头转向面对海盗岛，船只背对镜头，这样方便演示海盗劫持动画，完了后再恢复之前的镜头你觉得呢'
ROOT = Path('F:/马尼拉godot/manila-godot/demo/tropical_harbor_3d')

async def main():
    env = dict(os.environ, BLENDER_HOST='127.0.0.1', BLENDER_PORT='9881', DISABLE_TELEMETRY='true', BLENDERMCP_NO_UPDATE_CHECK='1', PYTHONUTF8='1')
    exe = Path(os.environ['LOCALAPPDATA']) / 'ManilaBlenderMCP/venv/Scripts/mcp-for-blender.exe'
    async with stdio_client(StdioServerParameters(command=str(exe), args=[], env=env)) as streams:
        async with ClientSession(*streams, read_timeout_seconds=timedelta(seconds=240)) as session:
            await session.initialize()
            report = []
            for name, args in [('get_addon_status', {}), ('get_scene_info', {'root':'P25_Assembly','limit':3,'fields':['settings','location','rotation','children']})]:
                result = await session.call_tool(name, dict(args, user_prompt=PROMPT))
                report.append({'tool':name, 'result':result.model_dump(mode='json')})
                print('\n'.join(x.text for x in result.content if hasattr(x,'text')))
                if result.isError:
                    raise RuntimeError(name)
            (ROOT/'captures/pirate_orientation_20261125/mcp_initial_info.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

if __name__=='__main__': asyncio.run(main())
