# Báo cáo thực hiện Lab: Tích hợp MCP Server & Tools (Order Tracking)

Dự án này triển khai một hệ thống **Model Context Protocol (MCP) Server** hoàn chỉnh từ bài toán thực tế hằng ngày (Tra cứu đơn hàng), hỗ trợ bảo mật (Authentication), phân phiên bản (Versioning) và tương thích với các MCP Client như Claude Code.

---

## 📌 Bước 1 - Use Case

- **Công việc hiện tại:** Tra cứu và theo dõi trạng thái đơn hàng cho khách hàng trong hệ thống bán lẻ.
- **Tôi đang làm thủ công như thế nào:** Khi khách hàng hỏi "Đơn hàng ORD-001 của tôi đến đâu rồi?", nhân viên phải mở phần mềm quản lý kho/Excel, tìm kiếm theo mã đơn hàng, xem trạng thái, copy thông tin sản phẩm và ngày giao dự kiến rồi gõ lại trả lời cho khách.
- **Input:** Mã đơn hàng (ví dụ: `ORD-001`) hoặc Trạng thái đơn hàng (ví dụ: `shipping`, `delivered`, `pending`).
- **Output:** Dữ liệu đơn hàng chi tiết: Tên khách hàng, danh sách sản phẩm, tổng tiền, trạng thái giao hàng, ngày cập nhật và ngày nhận hàng dự kiến.

---

## 🛠️ Bước 2 - Tools Design

Hệ thống được thiết kế với các tools thực hiện tác vụ thật (đọc dữ liệu từ cơ sở dữ liệu `data/orders.json`):

1. **`get_order(order_id: str)`** *(v1 - Legacy)*
   - **Mục đích:** Tra cứu trạng thái cơ bản của đơn hàng (dành cho client cũ).
   - **Input:** `order_id` (str)
   - **Output:** `{"status": "shipping"}`
2. **`get_order_v2(order_id: str, include_items: bool = True)`** *(v2 - New)*
   - **Mục đích:** Tra cứu toàn bộ thông tin chi tiết của đơn hàng.
   - **Input:** `order_id` (str), `include_items` (bool, default: `True`)
   - **Output:** `{"id": "ORD-001", "status": "shipping", "customer": "Nguyen Van A", "total_price": 1500000, "expected_delivery": "2026-08-30", "items": [...]}`
3. **`search_orders(status: str)`**
   - **Mục đích:** Tìm danh sách tất cả các đơn hàng theo trạng thái.
   - **Input:** `status` (str, ví dụ: `shipping`, `delivered`, `pending`)
   - **Output:** Danh sách các đơn hàng khớp trạng thái kèm số lượng.

---

## 🚀 Bước 3 - Run (Khởi chạy Server)

### Cấu trúc thư mục:
```
my-mcp-server/
├── data/
│   └── orders.json          # Database đơn hàng
├── server.py                # MCP Server chính (hỗ trợ stdio & Streamable HTTP)
├── client.py                # Client kiểm thử tự động
├── requirements.txt         # Thư viện phụ thuộc
└── README.md                # Tài liệu hướng dẫn
```

### Chạy Server:
Cài đặt thư viện:
```bash
uv pip install -r requirements.txt
# hoặc: pip install -r requirements.txt
```

1. **Chạy ở chế độ Streamable HTTP (Mặc định - cổng 8080):**
```bash
python server.py
```
*(Server lắng nghe tại `http://localhost:8080/mcp`)*

2. **Chạy ở chế độ `stdio` (dành cho Claude Code kết nối trực tiếp qua Process):**
```bash
python server.py --transport stdio
```

---

## 🤖 Bước 4 - Đăng ký vào Claude Code

Để Claude Code tự động nhận diện và gọi các tools từ Server:

### Cách 1: Đăng ký qua file cấu hình `claude_desktop_config.json` (hoặc Claude Code config):
```json
{
  "mcpServers": {
    "order-tracking": {
      "command": "python",
      "args": [
        "d:/AI_in_Action/Labs/Day26-MCP-Tools-Integration/my-mcp-server/server.py",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

### Cách 2: Đăng ký qua lệnh CLI của Claude Code:
```bash
claude mcp add order-tracking python d:/AI_in_Action/Labs/Day26-MCP-Tools-Integration/my-mcp-server/server.py --transport stdio
```

### Thử nghiệm prompt qua ngôn ngữ tự nhiên:
- *"Tìm giúp tôi các đơn hàng đang ở trạng thái shipping."*
- *"Tra cứu chi tiết đơn hàng ORD-001 xem khi nào giao hàng và gồm những món gì."*

**Luồng hoạt động:**
```
User hỏi: "Đơn hàng ORD-001 có những món gì?"
   │
   ▼
Claude Code (chọn tool `get_order_v2` với `order_id="ORD-001"`)
   │
   ▼ [Giao thức MCP]
MCP Server (`server.py` thực thi đọc `orders.json`)
   │
   ▼
Trả về JSON kết quả cho Claude Code
   │
   ▼
Claude Code tổng hợp câu trả lời tự nhiên cho người dùng.
```

---

## 🔐 Bước 5 - Authentication (Bảo mật cho HTTP Transport)

Server triển khai lớp `StaticTokenVerifier` kế thừa `TokenVerifier` từ MCP SDK:

- **Cơ chế:** Client truyền Bearer token qua HTTP Header `Authorization: Bearer secret-token-123`.
- **Token hợp lệ mặc định:** `secret-token-123` (hoặc cấu hình qua biến môi trường `MCP_AUTH_TOKEN`).
- **Kết quả kiểm thử bảo mật:**
  - ✅ **Token đúng:** Cho phép khởi tạo Session MCP và gọi toàn bộ tools.
  - ❌ **Không có token:** Server từ chối kết nối với mã lỗi `401 Unauthorized`.
  - ❌ **Token sai:** Server từ chối kết nối với mã lỗi `401/403`.

Chạy script kiểm thử bảo mật tự động:
```bash
python client.py
```

---

## 🔄 Bước 6 - Versioning & Backward Compatibility

1. **Format cũ (v1):** `{"status": "shipping"}`
2. **Format mới (v2):** Có thêm `customer`, `updated_at`, `expected_delivery`, `total_price`, `items`.
3. **Chiến lược tương thích ngược:**
   - Giữ nguyên tool `get_order` (v1) cho các hệ thống cũ không bị crash.
   - Bổ sung tool mới `get_order_v2` với tham số optional `include_items=True`.
   - Cung cấp Resource **`server://info`**:
     ```json
     {
       "name": "order-mcp",
       "version": "2.0.0",
       "tools": {
         "get_order": { "version": "1.0.0", "deprecated": true },
         "get_order_v2": { "version": "2.0.0", "deprecated": false },
         "search_orders": { "version": "1.0.0", "deprecated": false }
       },
       "migration_guide": "Khuyến nghị sử dụng get_order_v2 thay thế get_order."
     }
     ```
4. **Client Fallback Logic:** Client đọc `server://info` hoặc danh sách `list_tools()`. Nếu có `get_order_v2` sẽ ưu tiên sử dụng, nếu không sẽ tự động fallback về `get_order`.

---

## 📦 Bước 7 - Hoàn thiện Repository & Đẩy code

Toàn bộ mã nguồn đã được tổ chức khoa học và đẩy lên GitHub:

```bash
git status
git add .
git commit -m "Complete Day26 MCP Tools Integration"
git push
```
