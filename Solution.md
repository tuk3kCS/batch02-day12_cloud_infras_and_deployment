# Day 12 Lab - Mission Answers

> URL: https://batch02-day12cloudinfrasanddeployment-production.up.railway.app/
> Dashboard: https://batch02-day12cloudinfrasanddeployment-production.up.railway.app/dashboard

---

## Part 1: Localhost vs Production

### Exercise 1.1: Phát hiện anti-patterns trong file develop/app.py
Đọc mã nguồn `01-localhost-vs-production/develop/app.py`, ta phát hiện 5 lỗi thiết kế nghiêm trọng (anti-patterns) sau:
1. **Lộ thông tin nhạy cảm (Hardcoded Secrets):** Khai báo trực tiếp `OPENAI_API_KEY = "sk-..."` và `DATABASE_URL` trong mã nguồn. Nếu đẩy code lên GitHub, key và mật khẩu DB sẽ bị lộ ngay lập tức.
2. **Thiếu quản lý cấu hình (No Config Management):** Các biến cấu hình hệ thống như `DEBUG = True`, `MAX_TOKENS = 500` được định nghĩa cứng trong code, không thể tùy biến linh hoạt khi chạy trên các môi trường khác nhau.
3. **Ghi log bằng hàm `print()`:** Print không ghi nhận thời gian, cấp độ log (INFO, ERROR) và không ghi log ra định dạng JSON cấu trúc. Ngoài ra, việc print khóa API (`OPENAI_API_KEY`) ra màn hình là vi phạm nghiêm trọng về bảo mật.
4. **Không có Endpoint kiểm tra sức khỏe (No Health Check):** Khi ứng dụng bị treo (deadlock/memory leak), nền tảng cloud hoặc load balancer không có cách nào phát hiện để khởi động lại container.
5. **Cấu hình mạng cứng (Hardcoded Port/Host):** Thiết lập `host="localhost"` và `port=8000` khiến ứng dụng không thể lắng nghe traffic từ ngoài container, đồng thời bật `reload=True` gây lãng phí tài nguyên và rủi ro bảo mật trong production.

### Exercise 1.3: So sánh phiên bản Basic vs Advanced

| Feature | Basic | Advanced | Tại sao quan trọng? |
|---------|-------|----------|---------------------|
| **Config** | Hardcode trong code | Sử dụng các biến môi trường (`os.getenv`) | Bảo mật thông tin nhạy cảm, dễ dàng chuyển đổi cấu hình giữa dev/production mà không cần chỉnh sửa mã nguồn. |
| **Health check** | Không có | Cung cấp endpoints `/health` và `/ready` | Giúp hệ thống Cloud (Railway/Render/Kubernetes) giám sát tình trạng container, tự khởi động lại khi crash và điều phối traffic an toàn. |
| **Logging** | Dùng `print()` thông thường | JSON Structured Logging | Thuận tiện cho việc thu thập logs tập trung (Log Aggregation) và phân tích tìm lỗi tự động trên hệ thống quy mô lớn. |
| **Shutdown** | Ngắt đột ngột tiến trình | Graceful Shutdown (Bắt tín hiệu `SIGTERM`) | Đảm bảo hoàn thành các request của khách hàng đang xử lý trước khi tiến trình chính bị tắt hoàn toàn. |

---

## Part 2: Docker Containerization

### Exercise 2.1: Phân tích Dockerfile cơ bản (`02-docker/develop/Dockerfile`)
1. **Base image là gì?**
   - Base image được chọn là `python:3.11` (Bản phân phối Python đầy đủ, dung lượng lớn ~1 GB).
2. **Working directory là gì?**
   - Thư mục làm việc mặc định bên trong container được thiết lập là `/app`.
3. **Tại sao COPY requirements.txt trước?**
   - Để tối ưu hóa **Docker Layer Cache**. Do các dependency ít khi thay đổi hơn mã nguồn ứng dụng, việc copy và cài đặt dependencies trước sẽ giúp Docker tái sử dụng cache của bước này cho các lần build sau, chỉ thực hiện build lại từ bước copy mã nguồn.
4. **CMD vs ENTRYPOINT khác nhau thế nào?**
   - `CMD` khai báo câu lệnh hoặc đối số mặc định chạy khi khởi động container và dễ dàng bị ghi đè khi ta truyền tham số mới trong lệnh `docker run`.
   - `ENTRYPOINT` quy định lệnh thực thi chính cố định cho container (không bị ghi đè trực tiếp), các đối số truyền vào từ `docker run` hoặc `CMD` sẽ được nối tiếp làm đối số cho lệnh này.

### Exercise 2.2: Kích thước Image (Develop vs Production)
* **Kích thước Image của Develop (`my-agent:develop`):** Khoảng **1.66 GB** (Content size: **424 MB**) do sử dụng base image `python:3.11` đầy đủ, bao gồm toàn bộ hệ điều hành Debian và các thư viện biên dịch cồng kềnh (gcc, compiler, v.v.).
* **Kích thước Image của Production (`my-agent:advanced`):** Chỉ khoảng **~150 MB** nhờ sử dụng base image rút gọn `python:3.11-slim` ở stage chạy chính và loại bỏ hoàn toàn các compiler dư thừa từ stage builder. Kích thước giảm tới **90%** giúp tăng tốc độ tải và giảm không gian lưu trữ đáng kể.

### Exercise 2.3: Phân tích Multi-stage Build Dockerfile (`02-docker/production/Dockerfile`)
* **Stage 1 (Builder):** Sử dụng image đầy đủ để cài đặt các công cụ build hệ thống (gcc, headers) và cài đặt dependencies Python vào thư mục local `/root/.local`.
* **Stage 2 (Runtime):** Sử dụng base image gọn nhẹ `python:3.11-slim`, tạo user phi quản trị `agent` để chạy ứng dụng và chỉ copy các thư viện đã được cài đặt ở Stage 1 cùng mã nguồn sang.
* **Tại sao image nhỏ hơn?**
  * Do sử dụng phiên bản base image `-slim` rút gọn.
  * Loại bỏ hoàn toàn các trình biên dịch cồng kềnh (như gcc, make, dev-libraries) không cần thiết ở môi trường runtime. Kích thước image giảm từ ~1.03 GB xuống chỉ còn khoảng **~150 MB** (tiết kiệm hơn 85% dung lượng).

### Exercise 2.4: Phân tích Docker Compose Stack
* **Services khởi động:** `agent` (backend FastAPI), `redis` (cache state), `qdrant` (vector database), và `nginx` (load balancer/reverse proxy).
* **Cơ chế giao tiếp nội bộ:**
  * Toàn bộ các service nằm trong cùng một mạng ảo biệt lập (`internal` bridge network).
  * Các service liên kết với nhau bằng cách gọi hostname chính là tên của dịch vụ (ví dụ: `redis:6379`, `qdrant:6333`, `agent:8000`).
  * Chỉ duy nhất cổng HTTP/HTTPS (80/443) của `nginx` được ánh xạ ra ngoài máy host để tiếp nhận traffic từ người dùng, còn các database và backend hoàn toàn được ẩn giấu trong mạng nội bộ.

---

## Part 3: Cloud Deployment

### Exercise 3.2: So sánh render.yaml vs railway.toml
* **`render.yaml` (Render Blueprint):** Định nghĩa toàn bộ kiến trúc hạ tầng dạng mã nguồn (Infrastructure as Code - IaC) bao gồm các dịch vụ web, database, vùng địa lý, cấu hình RAM/CPU và cách liên kết các biến môi trường. Render sẽ tự động dựng toàn bộ tài nguyên này khi kết nối Git.
* **`railway.toml` (Railway Config):** Chỉ định nghĩa các thông số build (Dockerfile path) và cách giám sát ứng dụng (healthcheck path, restart policy). Railway quản lý tài nguyên phần cứng và các biến môi trường trực tiếp trên Web Dashboard/CLI chứ không lưu ở file này.

### Exercise 3.3: GCP Cloud Run CI/CD Pipeline
* **`cloudbuild.yaml`:** Định nghĩa các bước build tự động (CI) trên GCP: tải mã nguồn, build Docker image bằng Buildkit, push image lên Artifact Registry, và triển khai tự động lên Cloud Run.
* **`service.yaml`:** Khai báo cấu hình khai triển ứng dụng trên Cloud Run (số lượng CPU, dung lượng RAM, cổng lắng nghe, các biến môi trường liên kết an toàn với Secret Manager cho `OPENAI_API_KEY`).

---

## Part 4: API Security

### Exercise 4.1: API Key Authentication
* **API key được check ở đâu:** Check trong hàm dependency `verify_api_key` (FastAPI Depends) bằng cách đọc giá trị từ header `X-API-Key`.
* **Điều gì xảy ra nếu sai key:** Thiếu header key trả về lỗi `401 Unauthorized`. Có truyền key nhưng sai trả về lỗi `403 Forbidden` (hoặc `401 Unauthorized` tùy theo logic cấu hình).
* **Làm sao rotate key:** Đổi giá trị của biến môi trường `AGENT_API_KEY` trên cấu hình Railway/Render Dashboard và restart lại container mà không cần chỉnh sửa mã nguồn hay build lại Docker Image.

### Exercise 4.2: JWT Authentication (Advanced Flow)
Quy trình xác thực dựa trên JSON Web Token (JWT):
1. **Lấy Token:** Người dùng gửi `username` và `password` tới endpoint `/token` bằng phương thức POST.
2. **Ký số:** Server xác thực thông tin đăng nhập, nếu đúng sẽ sinh ra chuỗi mã hóa JWT chứa thời gian hết hạn (`exp`) và được ký số bằng thuật toán HMAC-SHA256 với một khóa bí mật (`SECRET_KEY`).
3. **Lưu trữ:** Client nhận JWT và lưu trữ (thường trong LocalStorage hoặc HttpOnly Cookie).
4. **Gửi yêu cầu:** Trong các request tiếp theo tới endpoint cần bảo vệ, Client đính kèm token vào header dạng: `Authorization: Bearer <token>`.
5. **Xác thực:** Middleware trên Server giải mã token bằng `SECRET_KEY`, kiểm tra tính toàn vẹn và hạn sử dụng. Nếu hợp lệ, request sẽ được xử lý.

### Exercise 4.4: Cost Guard (Kiểm soát ngân sách bằng Redis)
Mã nguồn xử lý kiểm tra ngân sách sử dụng của user hàng tháng:
```python
import redis
from datetime import datetime

r = redis.Redis()

def check_budget(user_id: str, estimated_cost: float) -> bool:
    # Lấy định dạng tháng hiện tại làm key (ví dụ: "2026-06")
    month_key = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"
    
    current = float(r.get(key) or 0)
    if current + estimated_cost > 10.0: # Giới hạn $10/tháng
        return False
    
    # Tăng hạn mức chi tiêu của user trên Redis
    r.incrbyfloat(key, estimated_cost)
    r.expire(key, 32 * 24 * 3600)  # Đặt TTL 32 ngày để tự động giải phóng bộ nhớ
    return True
```

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health Checks (Liveness và Readiness Probes)
Mã nguồn triển khai các endpoint kiểm tra sức khỏe ứng dụng:
```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/health")
def health():
    """Liveness probe: Container còn phản hồi hay không"""
    return {"status": "ok"}

@app.get("/ready")
def ready():
    """Readiness probe: Đảm bảo sẵn sàng nhận traffic (đã kết nối DB/Redis)"""
    try:
        # Kiểm tra kết nối Redis
        _redis.ping()
        # Kiểm tra kết nối Database (ví dụ)
        # db.execute("SELECT 1")
        return {"status": "ready"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {exc}")
```

### Exercise 5.2: Graceful Shutdown
Bắt tín hiệu `SIGTERM` từ hệ thống điều phối container để tắt máy an toàn:
```python
import signal
import sys
import time

def shutdown_handler(signum, frame):
    print("Ghi nhận tín hiệu SIGTERM. Đang tắt ứng dụng gracefully...")
    # 1. Đặt trạng thái sẵn sàng về False để liveness/readiness probe trả về lỗi (ngừng nhận traffic mới)
    global _is_ready
    _is_ready = False
    
    # 2. Đợi hoàn thành các request đang xử lý (ví dụ: sleep nhẹ hoặc đợi connection pool trống)
    time.sleep(2)
    
    # 3. Đóng các connection pool (Redis, Postgres)
    if _redis is not None:
        _redis.close()
        
    print("Dọn dẹp hoàn tất. Thoát tiến trình.")
    sys.exit(0)

# Liên kết handler với tín hiệu tắt máy hệ thống
signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)
```

### Exercise 5.3: Stateless Design
* **Khái niệm:** Không lưu trữ bất kỳ trạng thái phiên làm việc nào (như lịch sử chat, lượt đếm rate limit) trong bộ nhớ RAM của tiến trình backend.
* **Tại sao cần thiết:** Khi ứng dụng scale-out chạy nhiều replica hoặc nhiều workers song song, bộ cân bằng tải sẽ điều phối request ngẫu nhiên. Nếu thiết kế stateful (lưu ở RAM), người dùng sẽ liên tục bị mất lịch sử chat hoặc rate limit hoạt động sai lệch.
* **Giải pháp:** Chuyển toàn bộ dữ liệu trạng thái sang lưu tập trung tại **Redis** dùng chung.

### Exercise 5.4: Load Balancing với Nginx
* **Lệnh chạy scale:** `docker compose up --scale agent=3`
* **Nguyên lý hoạt động:** Nginx nhận request từ cổng 80/443 bên ngoài và sử dụng thuật toán vòng tròn (Round Robin) để chia đều request tới 3 container backend `agent`. Nếu 1 container bị chết, Nginx sẽ tự phát hiện thông qua health check và loại bỏ container lỗi ra khỏi danh sách điều hướng mà không làm gián đoạn trải nghiệm người dùng.

---

## Part 6: Final Project & Bonus Point Exercise

### 1. Kiến trúc hoàn chỉnh của Final Project (06-lab-complete)
* **Frontend:** Ứng dụng Single Page App viết bằng React + Vite + TypeScript được biên dịch thành thư mục tĩnh `frontend-dist/` và được FastAPI phục vụ tại subpath `/dashboard/`.
* **Backend:** Ứng dụng FastAPI chạy 2 workers, tích hợp API Key Auth, Rate Limiting, Cost Guard, Graceful Shutdown, và Health checks.
* **State Store:** Dùng Redis để lưu trữ toàn bộ trạng thái phiên, đồng bộ logs và đồng bộ request counters của cả hai worker để tránh phân mảnh trạng thái khi chạy đa tiến trình.

### 2. CI/CD Pipeline bằng GitHub Actions (Bonus Exercise)
Tôi đã xây dựng một quy trình CI/CD hoàn chỉnh tự động hóa 3 giai đoạn (Linting, Testing & Coverage, và Deployment) tại đường dẫn [.github/workflows/ci.yml](file:///d:/project/batch02-day12_cloud_infras_and_deployment/.github/workflows/ci.yml) kết hợp với bộ kiểm thử tự động tại [test_agent.py](file:///d:/project/batch02-day12_cloud_infras_and_deployment/06-lab-complete/tests/test_agent.py):

* **Bộ kiểm thử tự động (Unit Tests):** Được lưu tại [test_agent.py](file:///d:/project/batch02-day12_cloud_infras_and_deployment/06-lab-complete/tests/test_agent.py) sử dụng thư viện `pytest` và `TestClient` của FastAPI để tự động kiểm thử các endpoint `/health`, `/ready`, `/` và `/ask` (xác thực lỗi 401 khi thiếu API key).
* **Mã nguồn cấu hình Github Actions (.github/workflows/ci.yml):**
```yaml
name: Production CI/CD Pipeline

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  lint:
    name: Code Linting
    runs-on: ubuntu-latest
    steps:
    - name: Check out repository
      uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install Lint Tools
      run: |
        python -m pip install --upgrade pip
        pip install flake8 black

    - name: Verify Code Style (Black)
      run: black --check 06-lab-complete/app/

    - name: Lint with Flake8
      run: |
        flake8 06-lab-complete/app/ --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 06-lab-complete/app/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

  test:
    name: Unit Tests & Coverage
    runs-on: ubuntu-latest
    steps:
    - name: Check out repository
      uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r 06-lab-complete/requirements.txt
        pip install pytest pytest-cov httpx

    - name: Run Tests with Coverage
      run: |
        export PYTHONPATH=06-lab-complete
        pytest --cov=app --cov-report=xml --cov-report=term-missing 06-lab-complete/tests/

  deploy:
    name: Continuous Deployment (Railway)
    needs: [lint, test]
    runs-on: ubuntu-latest
    if: (github.ref == 'refs/heads/main' || github.ref == 'refs/heads/master') && github.event_name == 'push'
    steps:
    - name: Check out repository
      uses: actions/checkout@v3

    - name: Install Railway CLI
      run: npm i -g @railway/cli

    - name: Deploy to Railway
      run: railway up
      env:
        RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

### 3. Cấu hình Giám sát Prometheus (Bonus Exercise)
Tôi đã cấu hình file [prometheus.yml](file:///d:/project/batch02-day12_cloud_infras_and_deployment/prometheus.yml) phục vụ giám sát metrics hệ thống:
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'production-ai-agent'
    metrics_path: '/metrics'
    scheme: 'http'
    static_configs:
      - targets: ['localhost:8000']
```
Các file cấu hình trên đã được copy đầy đủ vào container chạy trên Railway (cấu hình trong Dockerfile) và đã được Dashboard ghi nhận trạng thái **configured** thành công.
