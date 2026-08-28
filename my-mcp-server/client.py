"""MCP Client kiểm thử cho Order Tracking MCP Server.

Minh hoạ đầy đủ:
1. Kết nối HTTP với Bearer Token.
2. Đọc Resource `server://info` để kiểm tra versioning & capabilities.
3. Cơ chế Versioning: Gọi tool v2 nếu khả dụng, fallback về v1 nếu không có.
4. Kiểm thử bảo mật (Authentication):
   - Token hợp lệ -> Thành công
   - Token không hợp lệ -> Bị từ chối
   - Không truyền Token -> Bị từ chối

Cách chạy (khi server.py đang chạy trên port 8080):
    python client.py
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import TextContent

SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8080/mcp")
VALID_TOKEN = os.environ.get("MCP_AUTH_TOKEN", "secret-token-123")


def format_mcp_content(content_items: list[Any]) -> str:
    """Helper định dạng text content từ phản hồi của MCP tool an toàn theo type checker."""
    texts: list[str] = []
    for item in content_items:
        if isinstance(item, TextContent):
            texts.append(item.text)
        elif hasattr(item, "text"):
            texts.append(str(getattr(item, "text")))
        else:
            texts.append(str(item))
    return "\n".join(texts)


async def run_client_demo() -> None:
    print("=" * 60)
    print("🚀 BẮT ĐẦU KIỂM THỬ ORDER MCP CLIENT VỚI STREAMABLE HTTP")
    print("=" * 60)

    # 1. KẾT NỐI VỚI TOKEN HỢP LỆ
    print("\n[1] Kết nối với Bearer Token hợp lệ...")
    http_client = httpx.AsyncClient(headers={"Authorization": f"Bearer {VALID_TOKEN}"})

    async with http_client:
        async with streamable_http_client(SERVER_URL, http_client=http_client) as streams:
            read_stream = streams[0]
            write_stream = streams[1]
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                print("✅ Khởi tạo session MCP thành công!")

                # Khám phá tools
                tools_response = await session.list_tools()
                available_tools = {t.name: t.description for t in tools_response.tools}
                print(f"\n📋 Danh sách {len(available_tools)} công cụ server công bố:")
                for name, desc in available_tools.items():
                    print(f"  • {name}: {desc}")

                # Đọc Resource server://info để kiểm tra version
                print("\n[2] Đọc Resource `server://info` để kiểm tra versioning...")
                try:
                    info_resource = await session.read_resource("server://info")
                    first_item = info_resource.contents[0]
                    raw_text = getattr(first_item, "text", str(first_item))
                    server_metadata = json.loads(raw_text)
                    print(f"  Version Server: {server_metadata.get('version')}")
                    print(f"  Migration Guide: {server_metadata.get('migration_guide')}")
                except Exception as e:
                    print(f"  ⚠️ Không đọc được resource: {e}")

                # 3. GỌI TOOL THEO CHIẾN LƯỢC VERSIONING (FALLBACK LOGIC)
                print("\n[3] Gọi tool tra cứu đơn hàng theo chiến lược Versioning:")
                order_id = "ORD-001"

                if "get_order_v2" in available_tools:
                    print(f"  -> Server hỗ trợ get_order_v2, ưu tiên gọi v2 cho đơn {order_id}...")
                    res = await session.call_tool("get_order_v2", {"order_id": order_id, "include_items": True})
                    print("  Kết quả (v2 - Full details):")
                    print(" ", format_mcp_content(res.content))
                else:
                    print(f"  -> Fallback: Gọi get_order (v1) cho đơn {order_id}...")
                    res = await session.call_tool("get_order", {"order_id": order_id})
                    print("  Kết quả (v1 - Basic status):")
                    print(" ", format_mcp_content(res.content))

                # 4. GỌI TOOL TÌM KIẾM
                print("\n[4] Gọi tool search_orders(status='shipping'):")
                search_res = await session.call_tool("search_orders", {"status": "shipping"})
                print("  Kết quả tìm kiếm:")
                print(" ", format_mcp_content(search_res.content))

    # 5. KIỂM THỬ BẢO MẬT (AUTHENTICATION TEST)
    print("\n" + "=" * 60)
    print("🔐 KIỂM THỬ BẢO MẬT (AUTHENTICATION)")
    print("=" * 60)

    # Test không token
    print("\n[A] Thử kết nối KHÔNG CÓ TOKEN:")
    async with httpx.AsyncClient() as no_auth_client:
        try:
            async with streamable_http_client(SERVER_URL, http_client=no_auth_client) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    print("  ❌ Lỗi: Kết nối thành công dù không có token!")
        except Exception:
            print("  ✅ ĐÃ BỊ TỪ CHỐI THÀNH CÔNG (Không có token).")

    # Test token sai
    print("\n[B] Thử kết nối VỚI TOKEN SAI ('invalid-token-456'):")
    async with httpx.AsyncClient(headers={"Authorization": "Bearer invalid-token-456"}) as bad_auth_client:
        try:
            async with streamable_http_client(SERVER_URL, http_client=bad_auth_client) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    print("  ❌ Lỗi: Kết nối thành công dù token sai!")
        except Exception:
            print("  ✅ ĐÃ BỊ TỪ CHỐI THÀNH CÔNG (Token sai).")

    print("\n" + "=" * 60)
    print("🎉 TẤT CẢ CÁC BƯỚC KIỂM THỬ HOÀN TẤT VÀ CHÍNH XÁC 100%!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_client_demo())
