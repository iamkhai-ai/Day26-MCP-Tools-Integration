"""Order Tracking MCP Server — Quản lý và tra cứu đơn hàng.

Hỗ trợ 2 chế độ transport:
1. stdio (dành cho Claude Code, Cursor, MCP Client cục bộ)
2. streamable-http (dành cho production, có Bearer Token authentication)

Versioning:
- v1: get_order (chỉ trả về status cơ bản)
- v2: get_order_v2 (trả về full JSON, có include_items, total_price, customer)
- search_orders: tìm kiếm theo trạng thái
- resource: server://info (công bố metadata version)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer

# 1. Setup Auth (TokenVerifier)
VALID_TOKENS: dict[str, str] = {
    os.environ.get("MCP_AUTH_TOKEN", "secret-token-123"): "admin-client",
    "prod-token-xyz789": "production-service",
}

class StaticTokenVerifier(TokenVerifier):
    """Xác thực Bearer token dựa trên danh sách token hợp lệ."""
    async def verify_token(self, token: str) -> AccessToken | None:
        client_id = VALID_TOKENS.get(token)
        if client_id is None:
            return None
        return AccessToken(token=token, client_id=client_id, scopes=["order:read"])

# 2. Khởi tạo MCP Server
mcp = MCPServer(
    "order-mcp",
    auth=AuthSettings(
        issuer_url="http://localhost:8080",
        resource_server_url="http://localhost:8080",
    ),
    token_verifier=StaticTokenVerifier(),
)

# 3. Đọc dữ liệu từ file JSON (Thao tác trên dữ liệu thật)
def load_orders() -> dict:
    data_file = Path(__file__).parent / "data" / "orders.json"
    if not data_file.exists():
        return {}
    with open(data_file, "r", encoding="utf-8") as f:
        return json.load(f)

# 4. Resources: Cung cấp versioning metadata cho client
@mcp.resource("server://info")
def get_server_info() -> str:
    """Metadata của server — version, supported tools, migration guide."""
    info = {
        "name": "order-mcp",
        "version": "2.0.0",
        "tools": {
            "get_order": {
                "version": "1.0.0",
                "deprecated": True,
                "description": "Lấy trạng thái đơn hàng (chuỗi status)"
            },
            "get_order_v2": {
                "version": "2.0.0",
                "deprecated": False,
                "description": "Lấy chi tiết đơn hàng (đầy đủ thông tin)"
            },
            "search_orders": {
                "version": "1.0.0",
                "deprecated": False,
                "description": "Tìm đơn hàng theo trạng thái"
            }
        },
        "migration_guide": "Khuyến nghị sử dụng get_order_v2 thay thế get_order để có đầy đủ thông tin chi tiết."
    }
    return json.dumps(info, ensure_ascii=False, indent=2)

# 5. Tools
@mcp.tool()
def get_order(order_id: str) -> str:
    """[v1] Tra cứu trạng thái của đơn hàng (bản cũ - backward compatibility).
    
    Args:
        order_id: Mã đơn hàng (ví dụ: ORD-001, ORD-002)
    """
    orders = load_orders()
    order = orders.get(order_id)
    if not order:
        return json.dumps({"error": f"Không tìm thấy đơn hàng mã {order_id}"}, ensure_ascii=False)
    
    # Bản v1: Chỉ trả về trạng thái
    return json.dumps({
        "status": order["status"]
    }, ensure_ascii=False)

@mcp.tool()
def get_order_v2(order_id: str, include_items: bool = True) -> str:
    """[v2] Tra cứu chi tiết của đơn hàng (bản mới - thông tin đầy đủ).
    
    Args:
        order_id: Mã đơn hàng (ví dụ: ORD-001, ORD-002)
        include_items: Có kèm danh sách sản phẩm hay không (mặc định True)
    """
    orders = load_orders()
    order = orders.get(order_id)
    if not order:
        return json.dumps({"error": f"Không tìm thấy đơn hàng mã {order_id}"}, ensure_ascii=False)
    
    # Bản v2: Trả về đầy đủ các trường
    result = {
        "id": order_id,
        "status": order["status"],
        "customer": order["customer"],
        "updated_at": order["updated_at"],
        "expected_delivery": order["expected_delivery"],
        "total_price": order["total_price"]
    }
    
    if include_items:
        result["items"] = order.get("items", [])
        
    return json.dumps(result, ensure_ascii=False)

@mcp.tool()
def search_orders(status: str) -> str:
    """Tìm danh sách các đơn hàng theo trạng thái.
    
    Args:
        status: Trạng thái cần tìm (shipping, delivered, pending)
    """
    orders = load_orders()
    results = []
    
    for order_id, data in orders.items():
        if data.get("status") == status:
            results.append({
                "id": order_id,
                "customer": data.get("customer"),
                "total_price": data.get("total_price"),
                "expected_delivery": data.get("expected_delivery")
            })
            
    return json.dumps({"results": results, "count": len(results)}, ensure_ascii=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Order Tracking MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="streamable-http",
        help="Transport giao tiếp (mặc định: streamable-http)",
    )
    parser.add_argument("--port", type=int, default=8080, help="Port cho HTTP server (mặc định: 8080)")
    parser.add_argument("--host", default="0.0.0.0", help="Host cho HTTP server (mặc định: 0.0.0.0)")
    args = parser.parse_args()

    if args.transport == "stdio":
        print("Starting Order MCP Server in stdio mode...", file=sys.stderr)
        mcp.run(transport="stdio")
    else:
        print(f"Starting Order MCP Server on http://{args.host}:{args.port}/mcp (Streamable HTTP)")
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
