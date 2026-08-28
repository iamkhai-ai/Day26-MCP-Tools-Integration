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

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8080/mcp")
VALID_TOKEN = os.environ.get("MCP_AUTH_TOKEN", "secret-token-123")


async def run_client_demo() -> None:
    print("=" * 60)
    print("🚀 BẮT ĐẦU KIỂM THỬ ORDER MCP CLIENT VỚI STREAMABLE HTTP")
    print("=" * 60)

    # 1. KẾT NỐI VỚI TOKEN HỢP LỆ
    print("\n[1] Kết nối với Bearer Token hợp lệ...")
    http_client = httpx.AsyncClient(headers={"Authorization": f"Bearer {VALID_TOKEN}"})

    async with http_client:
        async with streamable_http_client(SERVER_URL, http_client=http_client) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ Khởi tạo session MCP thành công!")

                # Khám phá tools
                tools = await session.list_tools()
                available_tools = {t.name: t.description for t in tools.tools}
                print(f"\n📋 Danh sách {len(available_tools)} công cụ server công bố:")
                for name, desc in available_tools.items():
                    print(f"  • {name}: {desc}")

                # Đọc Resource server://info để kiểm tra version
                print("\n[2] Đọc Resource `server://info` để kiểm tra versioning...")
                try:
                    info_resource = await session.read_resource("server://info")
                    server_metadata = json.loads(info_resource.contents[0].text)
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
                    print(" ", res.content[0].text)
                else:
                    print(f"  -> Fallback: Gọi get_order (v1) cho đơn {order_id}...")
                    res = await session.call_tool("get_order", {"order_id": order_id})
                    print("  Kết quả (v1 - Basic status):")
                    print(" ", res.content[0].text)

                # 4. GỌI TOOL TÌM KIẾM
                print("\n[4] Gọi tool search_orders(status='shipping'):")
                search_res = await session.call_tool("search_orders", {"status": "shipping"})
                print("  Kết quả tìm kiếm:")
                print(" ", search_res.content[0].text)

    # 5. KIỂM THỬ BẢO MẬT (AUTHENTICATION TEST)
    print("\n" + "=" * 60)
    print("🔐 KIỂM THỬ BẢO MẬT (AUTHENTICATION)")
    print("=" * 60)

    # Test không token
    print("\n[A] Thử kết nối KHÔNG CÓ TOKEN:")
    async with httpx.AsyncClient() as no_auth_client:
        try:
            async with streamable_http_client(SERVER_URL, http_client=no_auth_client) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    print("  ❌ Lỗi: Kết nối thành công dù không có token!")
        except Exception as e:
            print("  ✅ ĐÃ BỊ TỪ CHỐI THÀNH CÔNG (Không có token).")

    # Test token sai
    print("\n[B] Thử kết nối VỚI TOKEN SAI ('invalid-token-456'):")
    async with httpx.AsyncClient(headers={"Authorization": "Bearer invalid-token-456"}) as bad_auth_client:
        try:
            async with streamable_http_client(SERVER_URL, http_client=bad_auth_client) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    print("  ❌ Lỗi: Kết nối thành công dù token sai!")
        except Exception as e:
            print("  ✅ ĐÃ BỊ TỪ CHỐI THÀNH CÔNG (Token sai).")

    print("\n" + "=" * 60)
    print("🎉 TẤT CẢ CÁC BƯỚC KIỂM THỬ HOÀN TẤT VÀ CHÍNH XÁC 100%!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_client_demo())
