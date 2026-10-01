# Autonomous Software Team (Agentic + Multi-Model + Real-Time Dashboard)

Nền tảng điều phối lập trình tự động kết hợp vòng lặp kiểm thử/sửa lỗi tự trị (**Agentic Closed-Loop**) và bộ định tuyến đa mô hình linh hoạt (**Two-Tier Dynamic Model Routing**), đi kèm hệ thống giao diện trực quan hóa Dashboard thời gian thực trên **Next.js & React Flow**.

---

## 1. Kiến Trúc Cốt Lõi (Core Architecture)

```
                            ┌────────────────────────┐
                            │      USER REQUEST      │
                            └───────────┬────────────┘
                                        │
                                        ▼
                            ┌────────────────────────┐
                            │      TEAM LEADER       │
                            │  (Planner Engine)      │
                            │   - Phân rã mục tiêu   │
                            │   - Xây dựng đồ thị DAG│
                            └───────────┬────────────┘
                                        │
                                        ▼
                            ┌────────────────────────┐
                            │   TWO-TIER ROUTER      │
                            │  Tier 1: Task Category │
                            │  Tier 2: Model Picker  │
                            └───────────┬────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              ▼                         ▼                         ▼
        ┌───────────┐             ┌───────────┐             ┌───────────┐
        │ Subtask A │             │ Subtask B │             │ Subtask C │
        │ (Analysis)│             │  (Coding) │             │  (Review) │
        └─────┬─────┘             └─────┬─────┘             └─────┬─────┘
              │                         │                         │
              ▼                         ▼                         ▼
         [ Claude 3.5 ]             [ Codex / ]               [ Claude  ]
         [   Sonnet   ]             [ GPT-4o  ]               [  Opus   ]
              │                         │                         │
              └─────────────────────────┼─────────────────────────┘
                                        ▼
                            ┌────────────────────────┐
                            │     TOOL EXECUTOR      │
                            │   (Sandbox Runtime)    │
                            │  - File System, Diff   │
                            │  - Terminal Execution  │
                            └───────────┬────────────┘
                                        │
                                        ▼
                            ┌────────────────────────┐
                            │    VERIFIER / GATE     │
                            │  - Syntax / AST Parse  │
                            │  - Build & Compile     │
                            │  - Automated Test Pass │
                            └───────────┬────────────┘
                                        │
                               ┌────────┴────────┐
                               ▼                 ▼
                            [PASS]            [FAIL]
                               │                 │
                               ▼                 ▼
                           [FINISH]      ┌───────────────┐
                                         │   REPLANNER   │
                                         │ (Update DAG)  │
                                         └───────────────┘
                                                 │
                                                 └───────────────► [Router]
```

### Các nguyên tắc vận hành:
1. **Dynamic Model Routing:** Không cố định model cho một agent. Router định tuyến dựa trên Domain (Analysis, Implementation, Verification, Utility), độ phức tạp (Complexity 1-10) và ràng buộc chi phí (Cost constraint).
2. **Deterministic Quality Gate:** Kiểm tra khách quan (AST parsing, unit tests, linters). LLM không tự công nhận kết quả nếu Verifier chưa trả về trạng thái `PASS`.
3. **Adaptive Replanning:** Khi một node thất bại, đồ thị DAG giữ nguyên các node thành công trước đó và sinh các fix node nối tiếp để sửa lỗi dựa trên `error_trace`.

---

## 2. Cấu Trúc Dự Án (Project Structure)

```
Multi-Agent Software Team/
├── backend/
│   ├── app/
│   │   ├── schemas.py          # Data models: SubTask, GlobalDAGState, Events
│   │   ├── router.py           # Two-Tier Dynamic Model Router
│   │   ├── planner.py          # Goal Decomposition & Adaptive Replanner
│   │   ├── sandbox.py          # Workspace Tool Executor (fs, terminal, diffs)
│   │   ├── verifier.py         # Quality Gate (AST syntax, pytest runner)
│   │   ├── llm.py              # Multi-Provider Client (Claude, GPT, Gemini, Simulator)
│   │   ├── orchestrator.py     # Execution loop, DAG batching & WebSocket stream
│   │   └── main.py             # FastAPI REST & WebSocket Server
│   ├── tests/
│   │   └── test_system.py      # Unit test suite
│   ├── requirements.txt
│   └── run.py                  # Backend Launcher
├── frontend/
│   ├── app/
│   │   ├── layout.tsx          # Root Layout & Theme
│   │   ├── page.tsx            # AI Team Control Center Dashboard
│   │   └── globals.css         # Cyber-dark Theme & Glow Animations
│   ├── components/
│   │   ├── DAGCanvas.tsx       # Interactive React Flow Canvas (@xyflow/react)
│   │   ├── SubTaskNode.tsx     # Custom DAG Node with Model badges & States
│   │   ├── SessionStats.tsx    # Objective, Iterations, Cost & Progress
│   │   ├── AgentFleet.tsx      # Agent Fleet Status & Model Distribution %
│   │   ├── TerminalLog.tsx     # Real-Time Streaming Log & Filter
│   │   ├── CodeArtifactViewer.tsx # Workspace Artifacts & Unified Diff Viewer
│   │   ├── TaskModal.tsx       # New Objective Creation Modal
│   │   └── SettingsModal.tsx   # Model API Keys & Simulator Settings
│   └── package.json
├── workspace_sandbox/          # Isolated workspace for generated code & tests
├── start.bat                   # One-click startup script for Windows
├── start.ps1                   # PowerShell startup script
└── Multi-Agent Software Team.md # Technical Specification Reference
```

---

## 3. Hướng Dẫn Khởi Chạy (Quick Start)

### Cách 1: Khởi chạy 1-Click (Khuyên dùng trên Windows)
Nhấp đúp chuột vào file:
```cmd
start.bat
```
Hoặc chạy trên PowerShell:
```powershell
.\start.ps1
```

Script sẽ tự động khởi chạy:
- **Backend API:** `http://127.0.0.1:8000/docs`
- **Frontend Control Center:** `http://localhost:3000`

---

### Cách 2: Khởi chạy thủ công từng phần

#### 1. Khởi chạy Backend (FastAPI):
```powershell
$env:PYTHONPATH="backend"
.\backend\venv\Scripts\python backend/run.py
```

Chạy kiểm thử backend:
```powershell
$env:PYTHONPATH="backend"
.\backend\venv\Scripts\pytest -v backend/tests
```

#### 2. Khởi chạy Frontend (Next.js):
```powershell
cd frontend
npm run dev
```

Mở trình duyệt tại: `http://localhost:3000`

---

## 4. Các Tính Năng Trên Giao Diện Dashboard

1. **Live DAG Canvas:**
   - Trực quan hóa các subtask theo từng tầng thực thi song song (Topological batches).
   - Màu sắc trạng thái node:
     - `Gray`: Chờ thực thi (Pending).
     - `Cyan Glow Pulse`: Đang thực thi (Running).
     - `Green`: Hoàn thành, vượt qua Quality Gate (Passed).
     - `Red`: Thất bại kiểm thử (Failed).
     - `Orange Dotted Edge`: Đường nối từ node lỗi sang **Replan Fix Node**.
2. **Dynamic Model Allocation:**
   - Thống kê tỷ lệ phân bổ mô hình trong phiên (Claude 3.5 Sonnet, GPT-4o, Claude Opus, Gemini Pro, GPT-4o-mini).
3. **Real-Time Log Stream:**
   - Lọc log theo nguồn: `[Orchestrator]`, `[Router]`, `[Executor]`, `[Verifier]`, `[Sandbox]`, `[Replanner]`.
4. **Sandbox Diff & Code Viewer:**
   - Xem mã nguồn được sinh ra trong sandbox kèm **Unified Diff** chi tiết theo thời gian thực.
5. **Nút "Test Re-Plan Loop":**
   - Kích hoạt quy trình kiểm thử với lỗi cú pháp có chủ đích để quan sát Verifier Gate từ chối code và kích hoạt Adaptive Replanning mở rộng DAG tự động.
6. **Time Estimation & Live Execution Telemetry (Ước lượng thời gian & Đo lường thực tế):**
   - **Ước lượng theo từng subtask:** Tính toán thời gian dự kiến (`Est: ~XXs`) dựa trên Domain và Complexity (Lv.1–10).
   - **Critical Path Duration:** Ước lượng tổng thời gian cho toàn bộ pipeline dựa trên độ dài của từng tầng thực thi song song (Topological Batches).
   - **Live Progress & Variance:** Hiển thị thời gian chạy thực tế so với thời gian ước lượng trên từng node và thanh điều khiển bên trái.
