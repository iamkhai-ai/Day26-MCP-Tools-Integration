"""Order Tracking MCP Server
"""
import os
import json
from pathlib import Path

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer
from mcp.types import Resource

# 1. Setup Auth
VALID_TOKENS = {
    os.environ.get("MCP_AUTH_TOKEN", "secret-token-123"): "admin-client",
}

class StaticTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        client_id = VALID_TOKENS.get(token)
        if client_id is None:
            return None
        return AccessToken(token=token, client_id=client_id, scopes=["order:read"])

mcp = MCPServer(
    "order-mcp",
    auth=AuthSettings(
        issuer_url="http://localhost:8080",
        resource_server_url="http://localhost:8080",
    ),
    token_verifier=StaticTokenVerifier(),
)

# 2. Database loading function
def load_orders():
    data_file = Path(__file__).parent / "data" / "orders.json"
    if not data_file.exists():
        return {}
    with open(data_file, "r", encoding="utf-8") as f:
        return json.load(f)

# 3. Resources (Versioning info)
@mcp.resource("server://info")
def get_server_info() -> str:
    """Get information about the server version and available tools."""
    info = {
        "name": "order-mcp",
        "version": "2.0.0",
        "tools": {
            "get_order": {
                "version": "1.0.0",
                "deprecated": False
            },
            "get_order_v2": {
                "version": "2.0.0",
                "deprecated": False
            },
            "search_orders": {
                "version": "1.0.0",
                "deprecated": False
            }
        }
    }
    return json.dumps(info, indent=2)

# 4. Tools
@mcp.tool()
def get_order(order_id: str) -> str:
    """Tra cứu trạng thái của đơn hàng (v1). Trả về thông tin cơ bản.
    Args:
        order_id: Mã đơn hàng (VD: ORD-001)
    """
    orders = load_orders()
    order = orders.get(order_id)
    if not order:
        return json.dumps({"error": f"Không tìm thấy đơn hàng mã {order_id}"}, ensure_ascii=False)
    
    # v1 only returns basic status
    return json.dumps({
        "status": order["status"]
    }, ensure_ascii=False)

@mcp.tool()
def get_order_v2(order_id: str, include_items: bool = True) -> str:
    """Tra cứu chi tiết của đơn hàng (v2). Trả về thông tin đầy đủ.
    Args:
        order_id: Mã đơn hàng (VD: ORD-001)
        include_items: Có trả về danh sách sản phẩm không (mặc định True)
    """
    orders = load_orders()
    order = orders.get(order_id)
    if not order:
        return json.dumps({"error": f"Không tìm thấy đơn hàng mã {order_id}"}, ensure_ascii=False)
    
    result = {
        "id": order_id,
        "status": order["status"],
        "customer": order["customer"],
        "updated_at": order["updated_at"],
        "expected_delivery": order["expected_delivery"],
        "total_price": order["total_price"]
    }
    
    if include_items:
        result["items"] = order["items"]
        
    return json.dumps(result, ensure_ascii=False)

@mcp.tool()
def search_orders(status: str) -> str:
    """Tìm các đơn hàng theo trạng thái.
    Args:
        status: Trạng thái cần tìm (shipping, delivered, pending)
    """
    orders = load_orders()
    results = []
    
    for order_id, data in orders.items():
        if data.get("status") == status:
            results.append({
                "id": order_id,
                "customer": data["customer"]
            })
            
    return json.dumps({"results": results, "count": len(results)}, ensure_ascii=False)


if __name__ == "__main__":
    # Start server on streamable-http with port 8080
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)
