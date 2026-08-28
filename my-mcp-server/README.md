# Order Tracking MCP Server

Đây là một MCP Server mô phỏng quy trình Tra cứu đơn hàng (Order Tracking), được phát triển nhằm thực hành tích hợp Model Context Protocol (MCP) vào môi trường production.

## 📦 Use case
- **Công việc:** Tra cứu trạng thái đơn hàng.
- **Input:** Mã đơn hàng (`ORD-001`) hoặc trạng thái (`shipping`, `delivered`, `pending`).
- **Output:** Dữ liệu chi tiết của đơn hàng (thông tin khách hàng, sản phẩm, tổng giá, trạng thái, ngày cập nhật, ngày nhận hàng dự kiến).
- Dữ liệu được lưu trữ local trong thư mục `data/orders.json`.

## 🛠️ Các MCP Tools & Resources
Server cung cấp các tools sau để agent/LLM có thể gọi:

1. **`get_order(order_id: str)`** (v1)
   - Lấy thông tin cơ bản của đơn hàng (chỉ trả về trường `status`).
2. **`get_order_v2(order_id: str, include_items: bool)`** (v2)
   - Trả về thông tin đầy đủ của đơn hàng, có hỗ trợ bật/tắt hiển thị danh sách sản phẩm.
3. **`search_orders(status: str)`**
   - Tìm kiếm các đơn hàng dựa trên trạng thái cung cấp.

Ngoài ra, server cung cấp một Resource có URI `server://info` để thông báo các phiên bản (versioning metadata) của server và tools.

## 🚀 Cách chạy Server

Yêu cầu cài đặt môi trường (có thể dùng uv hoặc pip):
```bash
uv pip install -r requirements.txt
```

Khởi chạy MCP Server (chạy trên port 8080 với chuẩn Streamable HTTP):
```bash
python server.py
```

## 🔐 Authentication
Server được thiết lập để sử dụng Transport **streamable-http**. Do đó, mọi request phải kèm theo token xác thực hợp lệ thông qua header:
```
Authorization: Bearer secret-token-123
```
- Nếu không có token, hoặc token sai -> Server sẽ trả về `401 Unauthorized` hoặc `403 Forbidden`.
- Có thể thay đổi token mặc định bằng cách cấu hình biến môi trường `MCP_AUTH_TOKEN`.

## 🤖 Cách đăng ký vào Claude Code

Vì Server sử dụng kết nối HTTP + Authentication Token, cấu hình cho Claude Code (file `claude_desktop_config.json`) sẽ có dạng:

```json
{
  "mcpServers": {
    "order-tracking-server": {
      "command": "node",
      "args": [
        "path/to/some/http/client/connector.js"
      ],
      "env": {
        "URL": "http://localhost:8080/mcp",
        "BEARER_TOKEN": "secret-token-123"
      }
    }
  }
}
```
*(Ghi chú: Claude Code thường hỗ trợ stdio natively. Để kết nối HTTP có token, bạn có thể cần một mcp-client adaptor hoặc cấu hình SSE URL trực tiếp nếu Claude hỗ trợ `streamable-http` endpoint).*

Thử nghiệm prompt qua Claude Code:
- *"Tìm giúp tôi các đơn hàng đang shipping"*
- *"Thông tin chi tiết của đơn hàng ORD-001 là gì?"*

---
**Versioning**: 
Agent (Client) nên đọc resource `server://info` để biết server đang cung cấp những version tool nào. Nếu thấy `get_order_v2`, hãy ưu tiên dùng nó thay vì `get_order`.
