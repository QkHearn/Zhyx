"""测试 MCP 连接与工具"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


async def main():
    print("=== MCP 连接测试 ===\n")

    # 检查配置
    try:
        import yaml
        cfg_path = ROOT / "config" / "zhyx.yaml"
        with open(cfg_path, encoding="utf-8") as f:
            d = yaml.safe_load(f) or {}
        servers = (d.get("mcp") or {}).get("servers") or []
        print(f"配置的 MCP 服务器: {len(servers)} 个")
        for s in servers:
            print(f"  - {s.get('name', '?')}: {s.get('command')} {s.get('args', [])}")
    except Exception as e:
        print(f"[警告] 读取配置失败: {e}")

    try:
        import mcp
        print("mcp 包已安装\n")
    except ImportError:
        print("[失败] 请先执行: pip install mcp\n")
        return

    try:
        from mcp_client.client import mcp_session
    except ImportError as e:
        print(f"[失败] 无法导入 mcp_client: {e}")
        return

    print("正在连接 MCP 服务器（Puppeteer 首次可能需下载 Chromium，请稍候）...\n")
    async with mcp_session() as sess:
        tools = sess.get_openai_tools()
        if not tools:
            print("[失败] 未获取到任何 MCP 工具")
            print("可能原因: mcp.servers 配置为空，或连接 MCP 服务器失败")
            return

        print(f"[成功] 获取到 {len(tools)} 个工具:\n")
        for t in tools:
            fn = t.get("function") or {}
            name = fn.get("name", "?")
            desc = (fn.get("description") or "")[:80]
            print(f"  - {name}: {desc}...")

        # 尝试调用一个简单工具（优先 puppeteer_navigate，其次 fetch 的 fetch 等）
        call_name = None
        call_args = {}
        for t in tools:
            fn = t.get("function") or {}
            name = fn.get("name", "")
            if "puppeteer_navigate" in name or "navigate" in name:
                call_name = name
                call_args = {"url": "https://www.example.com"}
                break
            if "fetch" in name.lower() and "url" in str(fn.get("parameters", {})):
                call_name = name
                call_args = {"url": "https://www.example.com"}
                break

        if call_name:
            print(f"\n[测试] 调用工具: {call_name}({call_args})")
            try:
                result = await sess.call_tool(call_name, call_args)
                print(f"[成功] 返回:\n{result[:500]}..." if len(result) > 500 else f"[成功] 返回:\n{result}")
            except Exception as e:
                print(f"[失败] 调用异常: {e}")
        else:
            print("\n[跳过] 未找到可测试的 navigate/fetch 类工具")

    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
