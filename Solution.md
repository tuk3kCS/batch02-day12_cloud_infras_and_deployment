# Solutions for Day 12 Lab Exercises (Parts 1-5)

Tài liệu này tổng hợp toàn bộ câu trả lời cho các câu hỏi lý thuyết và bài tập thực hành từ Part 1 đến Part 5 trong nội dung môn học.

---

## Part 1: Localhost vs Production

### Exercise 1.3: So sánh app.py (Basic vs Advanced)

| Feature | Basic | Advanced | Tại sao quan trọng? |
|---------|-------|----------|---------------------|
| **Config** | Hardcode | Env vars (`os.getenv`) | Bảo mật thông tin nhạy cảm (không lộ API key trong mã nguồn khi push lên Git), dễ dàng chuyển đổi cấu hình giữa dev/production mà không cần sửa code. |
| **Health check** | Không có | Liveness & Readiness endpoints (`/health`, `/ready`) | Giúp các nền tảng đám mây (Railway/Render/Kubernetes) giám sát tình trạng container, tự khởi động lại khi crash và điều phối traffic an toàn. |
| **Logging** | `print()` | JSON Structured Logging | Thuận tiện cho việc thu thập logs tập trung (Log Aggregation) và phân tích tìm lỗi tự động trên hệ thống lớn. |
| **Shutdown** | Đột ngột | Graceful Shutdown (`SIGTERM`) | Đảm bảo server hoàn thành việc xử lý các request đang chạy của khách hàng trước khi tiến trình chính bị tắt hoàn toàn. |

---

## Part 2: Docker Containerization

### Exercise 2.1: Phân tích Dockerfile cơ bản
1. **Base image là gì?**
   - Base image là `python:3.11` (Bản phân phối Python đầy đủ, dung lượng lớn ~1 GB).
2. **Working directory là gì?**
   - Thư mục làm việc bên trong container được thiết lập là `/app`.
3. **Tại sao COPY requirements.txt trước?**
   - Để tận dụng cơ chế **Docker Layer Cache**. Do file requirements.txt rất ít khi thay đổi so với mã nguồn, việc copy và cài đặt dependencies trước giúp Docker không phải cài đặt lại thư viện ở những lần build sau nếu bạn chỉ chỉnh sửa code.
4. **CMD vs ENTRYPOINT khác nhau thế nào?**
   - `CMD` khai báo câu lệnh hoặc đối số mặc định khi chạy container và dễ dàng bị ghi đè (override) khi chạy lệnh `docker run`.
   - `ENTRYPOINT` quy định lệnh thực thi chính cố định cho container (không bị ghi đè trực tiếp), các đối số truyền vào từ `docker run` sẽ được nối tiếp sau lệnh này.

### Exercise 2.2: Kích thước Image cơ bản
* **Image size quan sát được:** Khoảng **1.03 GB** do sử dụng base image `python:3.11` đầy đủ (bao gồm cả các công cụ build hệ thống không cần thiết ở runtime).

### Exercise 2.3: Phân tích Multi-stage Build Dockerfile
* **Stage 1 (Builder):** Thực hiện cài đặt các công cụ build (gcc, headers) và cài đặt toàn bộ dependencies Python vào thư mục `/root/.local`.
* **Stage 2 (Runtime):** Sử dụng base image gọn nhẹ `python:3.11-slim`, tạo user không có quyền quản trị `agent` để chạy ứng dụng và chỉ sao chép các dependencies đã biên dịch từ Stage 1 cùng mã nguồn ứng dụng sang.
* **Tại sao image nhỏ hơn?**
  * Do sử dụng phiên bản base image `-slim` rút gọn.
  * Do loại bỏ hoàn toàn các trình biên dịch cồng kềnh (như gcc, dev-libraries) không cần thiết ở môi trường runtime. Kích thước image giảm mạnh từ ~1 GB xuống chỉ còn khoảng **~150 MB**.

### Exercise 2.4: Phân tích Docker Compose Stack
* **Services khởi động:** `agent` (backend FastAPI), `redis` (session/rate store), `qdrant` (vector database cho RAG), và `nginx` (load balancer/proxy).
* **Cơ chế giao tiếp nội bộ:**
  * Toàn bộ các service nằm trong cùng một mạng ảo biệt lập (`internal` bridge network).
  * Các service liên kết với nhau bằng cách gọi hostname chính là tên của dịch vụ (ví dụ: `redis:6379`, `qdrant:6333`, `agent:8000`).
  * Chỉ duy nhất cổng HTTP/HTTPS (80/443) của `nginx` được ánh xạ ra ngoài máy host, giữ cho cơ sở dữ liệu và backend được cô lập an toàn khỏi Internet.

---

## Part 3: Cloud Deployment

### Exercise 3.2: So sánh render.yaml vs railway.toml
* **`render.yaml` (Render Blueprint):** Định nghĩa toàn bộ kiến trúc hạ tầng dạng mã nguồn (Infrastructure as Code - IaC) bao gồm Web services, cơ sở dữ liệu, vùng địa lý, cấu hình RAM/CPU và cách liên kết các biến môi trường. Render sẽ tự động dựng toàn bộ tài nguyên này.
* **`railway.toml` (Railway Config):** Chỉ định nghĩa các thông số build (Dockerfile path) và cách giám sát ứng dụng (healthcheck path, restart policy). Railway quản lý tài nguyên và biến môi trường thông qua Web Dashboard/CLI chứ không lưu ở file này.

---

## Part 4: API Security

### Exercise 4.1: API Key Authentication
* **API key được check ở đâu:** Check trong hàm dependency `verify_api_key` (FastAPI Depends) bằng cách đọc giá trị từ header `X-API-Key`.
* **Điều gì xảy ra nếu sai key:** Thiếu header key trả về lỗi `401 Unauthorized`. Có truyền key nhưng sai trả về lỗi `403 Forbidden` (hoặc `401 Unauthorized` tùy theo logic cấu hình).
* **Làm sao rotate key:** Đổi giá trị của biến môi trường `AGENT_API_KEY` trên cấu hình Railway/Render Dashboard và restart lại container mà không cần chỉnh sửa mã nguồn hay build lại Docker Image.

### Exercise 4.3: Rate Limiting
* **Thuật toán sử dụng:** Thuật toán **Sliding Window Counter** sử dụng hàng đợi `deque` để lưu trữ timestamp của các request trong vòng 60 giây gần nhất.
* **Hạn mức giới hạn:** Mặc định phân cấp user thường là **10 requests/minute**, tài khoản admin là **100 requests/minute**.
* **Bypass limit cho admin:** Phân quyền vai trò (Role) cho User dựa trên API Key hoặc thông tin giải mã từ JWT token, sau đó chuyển hướng qua Limiter có hạn mức cao hơn hoặc bỏ qua kiểm tra rate limit hoàn toàn.

---

## Part 5: Scaling & Reliability

### Khái niệm cốt lõi:
* **Stateless Design:** Không lưu trữ trạng thái người dùng (như phiên chat, rate limit) trong RAM của backend vì khi scale-out ra nhiều worker hoặc container, request sẽ bị điều phối ngẫu nhiên giữa các worker dẫn tới mất dữ liệu. Trạng thái bắt buộc phải được lưu tập trung tại một database dùng chung như Redis.
* **Graceful Shutdown:** Lắng nghe tín hiệu `SIGTERM` từ container orchestrator, ngừng nhận request mới, hoàn thành nốt các request hiện tại trước khi đóng kết nối database và tắt hẳn tiến trình, giúp hệ thống đạt trạng thái zero-downtime khi deploy.
