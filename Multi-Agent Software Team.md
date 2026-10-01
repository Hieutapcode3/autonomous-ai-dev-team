# KIẾN TRÚC & HƯỚNG DẪN XÂY DỰNG HỆ THỐNG AUTONOMOUS SOFTWARE TEAM (AGENTIC + MULTI-MODEL + REAL-TIME DASHBOARD)

> **Mục tiêu:** Xây dựng nền tảng điều phối lập trình tự động kết hợp vòng lặp kiểm thử/sửa lỗi tự trị (**Agentic Closed-Loop**) và bộ định tuyến đa mô hình linh hoạt (**Per-Subtask Dynamic Model Routing**), đi kèm hệ thống giao diện trực quan hóa Dashboard thời gian thực.

---

## 1. TỔNG QUAN KIẾN TRÚC & NGUYÊN LÝ HOẠT ĐỘNG

Hệ thống hoạt động theo mô hình **Two-Tier Intelligence Pipeline** (Trí tuệ 2 tầng) tích hợp vòng lặp phản xạ khép kín:

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
                            │  - File System, Git    │
                            │  - Shell, Compilers    │
                            └───────────┬────────────┘
                                        │
                                        ▼
                            ┌────────────────────────┐
                            │    VERIFIER / GATE     │
                            │  - Syntax / Linter     │
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

### Nguyên tắc vận hành cốt lõi:
1. **Không gán cứng model vào Agent:** Một Agent (ví dụ: `Coder`) sẽ không bị cố định một model duy nhất. Tùy thuộc vào độ phức tạp, chi phí và tính chất của từng subtask trong DAG, Router sẽ tự động cấp phát mô hình tối ưu nhất.
2. **Deterministic Quality Gate:** Mọi bước thực thi code bắt buộc phải vượt qua các công cụ kiểm thử khách quan (Compiler, Linter, Test Runner). LLM không tự tuyên bố code chạy đúng nếu Verifier chưa trả về trạng thái `PASS`.
3. **Adaptive Replanning:** Khi xảy ra lỗi (Compile error, Test failure), hệ thống giữ nguyên các node thành công trước đó, chỉ cập nhật node bị lỗi và tạo các subtask khắc phục trong DAG.

---

## 2. BẢNG PHÂN TÍCH TECH STACK TỪ CÁC REPO THAM CHIẾU (REFERENCES)

Để hiện thực hóa hệ thống hoàn chỉnh từ Core Engine đến UI, chúng ta tích hợp các công nghệ đã được chứng minh hiệu quả từ hai repo gốc:

| Thành phần | Repo gốc: **AgentFlow** (`lupantech`) | Repo gốc: **Pi-Multi-Agent** (`jwangkun`) | Đề xuất tích hợp cho hệ thống Production |
| :--- | :--- | :--- | :--- |
| **Ngôn ngữ lõi** | Python (Pydantic, AsyncIO) | TypeScript (Strict mode, Node.js) | **Backend:** Python (FastAPI) hoặc Node.js (TypeScript)<br>**Frontend:** TypeScript |
| **Orchestration Core** | Vòng lặp `Planner -> Executor -> Verifier -> Generator` có bộ nhớ chia sẻ (*Shared Memory*). | Đồ thị phụ thuộc task DAG, bộ định tuyến (*Per-subtask Model Router*), vòng lặp đánh giá chất lượng (*DeepEvaluator*). | **Hybrid Core:** Khởi tạo đồ thị DAG & Dynamic Router (từ *Pi-Multi-Agent*), vòng lặp phản xạ Tool Executor/Verifier (từ *AgentFlow*). |
| **Model Backends** | Khung tích hợp hỗ trợ OpenAI API, vLLM / HuggingFace Transformers (tối ưu cục bộ cho Qwen-2.5-7B). | Đa nhà cung cấp: OpenAI, Anthropic, Google Gemini, OpenRouter, DeepSeek. | **Multi-Provider SDK:** Anthropic SDK, OpenAI SDK, Google GenAI SDK, LiteLLM (làm proxy thống nhất). |
| **Quản lý Sandbox** | Python Subprocess / Docker cơ bản cho môi trường toán học & suy luận. | Sandboxed JS/Node Pipeline, cách ly Process, token budget per session. | **Docker Container Isolation / E2B Sandbox Runtime** với Network Restriction. |
| **Giao diện người dùng (UI/UX)** | Streamlit / Gradio (Giao diện phục vụ Demo nghiên cứu). | **Next.js Real-Time Dashboard** kết nối qua **WebSocket** (theo dõi Agent status, stream logs, visual tiến trình). | **Next.js (App Router) + TailwindCSS + React Flow (@xyflow/react) + WebSocket / SSE.** |

---

## 3. THIẾT KẾ KIẾN TRÚC BỘ ĐỊNH TUYẾN HAI TẦNG (TWO-TIER ROUTER)

Thay vì thiết lập thủ công, Router hoạt động dựa trên logic 2 giai đoạn:

```
                  ┌────────────────────────────────────────┐
                  │          SUBTASK TỪ PLANNER            │
                  │  (Description, Context, Required Tools)│
                  └───────────────────┬────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │       TIER 1: TASK INTELLIGENCE        │
                  │       (Phân loại tính chất tác vụ)     │
                  └───────────────────┬────────────────────┘
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            ▼                         ▼                         ▼
     [Deep Reasoning]        [Core Implementation]       [Utility & Tool-Ops]
     (Math, System Design,   (Complex Algorithm,         (Command Execution,
      Root-cause Debugging)   Refactoring, Unit Tests)    Log Parsing, Syntax Check)
            │                         │                         │
            └─────────────────────────┼─────────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────┐
                  │       TIER 2: MODEL INTELLIGENCE       │
                  │   (Định lượng: Complexity vs Cost)     │
                  └───────────────────┬────────────────────┘
                                      │
       ┌──────────────────────────────┼──────────────────────────────┐
       ▼                              ▼                              ▼
 [High-Tier Models]           [Mid-Tier Models]             [Fast/Cost-Tier Models]
 - Claude 3 Opus              - Claude 3.5 Sonnet           - GPT-4o-mini
 - Gemini 1.5 Pro (Big Log)   - GPT-4o                      - Local SLMs (DeepSeek-Coder)
```

### Nguyên tắc chọn Model tổng quát:
* **Tác vụ Deep Reasoning / System Architecture (Độ phức tạp 8–10):** Ưu tiên các model có khả năng suy luận logic chuyên sâu, tránh ảo giác ở khâu phân tích bài toán (ví dụ: Claude 3 Opus hoặc OpenAI o1/GPT-4o).
* **Tác vụ Core Coding & Refactoring (Độ phức tạp 5–7):** Ưu tiên các model có năng lực sinh mã nguồn chuẩn xác, tuân thủ syntax nghiêm ngặt và hỗ trợ tool-call ổn định (ví dụ: Claude 3.5 Sonnet, GPT-4o).
* **Tác vụ Big-Context Parsing (Đọc log lớn, duyệt tài liệu dày):** Ưu tiên các model hỗ trợ Context Window lớn mà không suy giảm khả năng retrieval (ví dụ: Gemini 1.5 Pro/Flash).
* **Tác vụ Tool Execution & Parse Output (Độ phức tạp 1–4):** Ưu tiên các model nhẹ, phản hồi nhanh và chi phí thấp để chạy lệnh shell, đọc kết quả biên dịch và lọc output (ví dụ: GPT-4o-mini, Local SLMs).

---

## 4. QUY TRÌNH KỸ THUẬT & CẤU TRÚC CODE LÕI (CORE IMPLEMENTATION)

Dưới đây là thiết kế chuẩn xác theo mô hình Type-safe (Python + Pydantic hoặc TypeScript), dễ dàng tích hợp vào REST API hoặc WebSocket.

### 4.1 Schema Định Nghĩa Dữ Liệu (`schemas.py`)

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum

class TaskDomain(str, Enum):
    ANALYSIS = "analysis"
    ARCHITECTURE = "architecture"
    IMPLEMENTATION = "implementation"
    VERIFICATION = "verification"
    UTILITY = "utility"

class ModelProvider(str, Enum):
    CLAUDE_OPUS = "claude-3-opus"
    CLAUDE_SONNET = "claude-3-5-sonnet"
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    GEMINI_PRO = "gemini-1.5-pro"

class SubTask(BaseModel):
    task_id: str
    title: str
    description: str
    domain: TaskDomain
    complexity: int = Field(ge=1, le=10) # Thang điểm 1 - 10
    dependencies: List[str] = Field(default_factory=list) # Danh sách ID phải chạy trước
    assigned_model: Optional[ModelProvider] = None
    required_tools: List[str] = Field(default_factory=list)
    status: str = "pending" # pending | running | completed | failed
    output_artifacts: Optional[Dict[str, Any]] = None
    error_trace: Optional[str] = None

class GlobalDAGState(BaseModel):
    session_id: str
    objective: str
    tasks: Dict[str, SubTask]
    execution_order: List[List[str]] # Các tầng thực thi song song
    iteration: int = 0
    max_iterations: int = 5
    total_cost_usd: float = 0.0
```

### 4.2 Module Phân Loại & Điều Phối Mô Hình (`router.py`)

```python
class DynamicModelRouter:
    def __init__(self, cost_constrained: bool = False):
        self.cost_constrained = cost_constrained

    def route_task(self, task: SubTask) -> ModelProvider:
        # Tầng 1: Phân loại theo Task Domain & Ngữ cảnh
        if task.domain in [TaskDomain.ANALYSIS, TaskDomain.ARCHITECTURE]:
            if task.complexity >= 8 and not self.cost_constrained:
                return ModelProvider.CLAUDE_OPUS
            return ModelProvider.CLAUDE_SONNET

        # Tầng 2: Thực thi lập trình & Refactor
        if task.domain == TaskDomain.IMPLEMENTATION:
            if task.complexity >= 5:
                return ModelProvider.CLAUDE_SONNET
            return ModelProvider.GPT_4O

        # Tầng 3: Các tác vụ phân tích Log / Ngữ cảnh siêu lớn
        if "big_log_analysis" in task.required_tools:
            return ModelProvider.GEMINI_PRO

        # Tầng 4: Tác vụ tiện ích, parse dữ liệu, chạy lệnh shell
        if task.complexity <= 3 or task.domain == TaskDomain.UTILITY:
            return ModelProvider.GPT_4O_MINI

        return ModelProvider.CLAUDE_SONNET
```

### 4.3 Vòng Lặp Thực Thi & Re-Planning (`orchestrator.py`)

```python
class TeamOrchestrator:
    def __init__(self, state: GlobalDAGState, router: DynamicModelRouter, sandbox_runtime, verifier_gate):
        self.state = state
        self.router = router
        self.sandbox = sandbox_runtime
        self.verifier = verifier_gate

    async def execute_dag(self):
        while self.state.iteration < self.state.max_iterations:
            uncompleted_tasks = [t for t in self.state.tasks.values() if t.status != "completed"]
            if not uncompleted_tasks:
                return {"status": "SUCCESS", "message": "Toàn bộ DAG hoàn thành đạt chuẩn."}

            for parallel_batch in self.state.execution_order:
                batch_tasks = [self.state.tasks[tid] for tid in parallel_batch if self.state.tasks[tid].status == "pending"]
                
                # Chạy song song các task không phụ thuộc lẫn nhau
                for task in batch_tasks:
                    task.assigned_model = self.router.route_task(task)
                    task.status = "running"
                    await self.emit_websocket_event("TASK_STARTED", task)

                    # 1. Executor gọi Model và Tool trong Sandbox
                    exec_result = await self.sandbox.run_task(task)
                    
                    # 2. Verifier Gate kiểm tra kết quả (Compiler, Linter, Test)
                    verify_result = await self.verifier.evaluate(task, exec_result)

                    if verify_result["passed"]:
                        task.status = "completed"
                        task.output_artifacts = exec_result["artifacts"]
                        await self.emit_websocket_event("TASK_COMPLETED", task)
                    else:
                        task.status = "failed"
                        task.error_trace = verify_result["error_log"]
                        await self.emit_websocket_event("TASK_FAILED", task)
                        
                        # 3. Kích hoạt Re-planning: Cập nhật DAG thay vì crash
                        await self.trigger_replan(failed_task=task)
                        break # Dừng đợt thực thi hiện tại để tính toán lại đồ thị

            self.state.iteration += 1

        return {"status": "FAILED", "message": "Vượt quá số lần Replan cho phép."}

    async def trigger_replan(self, failed_task: SubTask):
        """Kế thừa kỹ thuật Planner-Refinement từ AgentFlow: sửa đổi và chèn thêm task giải quyết lỗi"""
        # Gọi Planner để sinh các node mới sửa lỗi dựa trên error_trace
        ...
```

---

## 5. THIẾT KẾ KIẾN TRÚC GIAO DIỆN (REAL-TIME DASHBOARD UI/UX)

Để có được một giao diện chuyên nghiệp giống như các Orchestration Platform hiện đại (tương tự Dashboard của *Pi-Multi-Agent*), hệ thống UI được chia thành các khối thành phần cụ thể:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        AI TEAM CONTROL CENTER                          │
├───────────────────┬────────────────────────────────────────────────────┤
│ 1. OBJECTIVE &    │ 3. LIVE DAG WORKFLOW (React Flow Canvas)           │
│    SESSION STATS  │                                                    │
│ ───────────────── │    ┌─────────┐      ┌─────────┐      ┌─────────┐   │
│ Target: [Bugfix]  │    │Task 1   │─────►│Task 2   │─────►│Task 3   │   │
│ Iteration: 2/5    │    │(Sonnet) │      │(Codex)  │      │(Opus)   │   │
│ Budget: $0.42     │    └─────────┘      └─────────┘      └────┬────┘   │
│ Status: RUNNING   │                                           │ (Fail) │
│                   │                                           ▼        │
│ ───────────────── │                                      ┌─────────┐   │
│ 2. AGENT FLEET    │                                      │Replan #1│   │
│ • Planner  [IDLE] │                                      │(GPT-4o) │   │
│ • Executor [BUSY] │                                      └─────────┘   │
│ • Verifier [WAIT] ├────────────────────────────────────────────────────┤
│                   │ 4. REAL-TIME LOG STREAM & TERMINAL (Xterm.js)      │
│ Model Allocation: │ [WebSocket] Subtask 2: Running compile check...    │
│ • Claude: 60%     │ [Compiler] Warning: CS0168 on line 42.             │
│ • GPT-4o: 30%     │ [Verifier] Exit code: 0. Test Suite Passed!        │
│ • Mini/SLM: 10%   │                                                    │
└───────────────────┴────────────────────────────────────────────────────┘
```

### 5.1 Tech Stack cho Giao diện Dashboard

1. **Framework nền tảng:**
   * **Next.js 14+ (App Router, React 18/19):** Xây dựng SSR/CSR hybrid dashboard.
   * **TailwindCSS + shadcn/ui:** Cung cấp theme Dark mode hiện đại, các component Card, Badge, Dialog, Progress Bar tinh gọn.
2. **Trực quan hóa Đồ thị DAG:**
   * **`@xyflow/react` (trước đây là React Flow):** Thư viện dựng Node-based graph tương tác cao.
   * Hiển thị trạng thái các Node theo màu sắc: 
     * `Xám` (Pending)
     * `Xanh dương viền phát sáng` (Running với icon Model tương ứng)
     * `Xanh lá` (Completed / Gate Passed)
     * `Đỏ` (Failed $\rightarrow$ kích hoạt đường link nét đứt dẫn đến Replan Node).
3. **Cơ chế truyền thông thời gian thực:**
   * **WebSocket / Server-Sent Events (SSE):** Backend phát các event `TASK_STARTED`, `TASK_PROGRESS`, `MODEL_SWITCHED`, `LOG_CHUNK`, `REPLAN_TRIGGERED`.
4. **Hiển thị Terminal & Diff:**
   * **`@xterm/xterm` (Xterm.js):** Render console log từ Sandbox theo chuẩn ANSI color.
   * **`react-diff-viewer-continued`:** Hiển thị chi tiết các đoạn code diff mà Executor vừa can thiệp vào mã nguồn.

### 5.2 Mẫu Component Trực Quan Hóa Node DAG (`DAGNode.tsx`)

```tsx
import React from 'react';
import { Handle, Position } from '@xyflow/react';

export function SubTaskNode({ data }: { data: any }) {
  const getBadgeColor = (model: string) => {
    if (model.includes('opus')) return 'bg-purple-900 text-purple-200 border-purple-500';
    if (model.includes('sonnet')) return 'bg-blue-900 text-blue-200 border-blue-500';
    if (model.includes('4o-mini')) return 'bg-emerald-900 text-emerald-200 border-emerald-500';
    return 'bg-amber-900 text-amber-200 border-amber-500';
  };

  return (
    <div className={`p-4 rounded-xl border-2 shadow-lg w-64 bg-slate-900 ${
      data.status === 'running' ? 'border-cyan-400 animate-pulse' :
      data.status === 'completed' ? 'border-green-500' :
      data.status === 'failed' ? 'border-red-500' : 'border-slate-700'
    }`}>
      <Handle type="target" position={Position.Top} className="w-3 h-3 bg-cyan-400" />
      
      <div className="flex justify-between items-center mb-2">
        <span className="text-xs font-mono text-slate-400">#{data.id}</span>
        <span className={`text-[10px] px-2 py-0.5 rounded-full border ${getBadgeColor(data.assignedModel)}`}>
          {data.assignedModel}
        </span>
      </div>

      <div className="font-bold text-sm text-slate-100 mb-1 truncate">{data.title}</div>
      <div className="text-xs text-slate-400 line-clamp-2 mb-3">{data.description}</div>

      <div className="flex justify-between items-center text-[11px] pt-2 border-t border-slate-800">
        <span className="capitalize text-slate-300 font-medium">Domain: {data.domain}</span>
        <span className="font-semibold text-cyan-400">Diff: Lv.{data.complexity}</span>
      </div>

      <Handle type="source" position={Position.Bottom} className="w-3 h-3 bg-cyan-400" />
    </div>
  );
}
```

---

## 6. LỘ TRÌNH TRIỂN KHAI HOÀN CHỈNH (STEP-BY-STEP ROADMAP)

Để đưa toàn bộ kiến trúc này vào hoạt động, quy trình thực hiện gồm 4 giai đoạn:

```
[ Giai đoạn 1 ] ──► [ Giai đoạn 2 ] ──► [ Giai đoạn 3 ] ──► [ Giai đoạn 4 ]
Thiết lập Sandbox    Xây dựng Routing     Khép kín vòng lặp    Phát triển Dashboard
& Tool Primitive     & State Graph        Verifier & Replan    & WebSocket Hub
```

1. **Giai đoạn 1 - Sandbox & Tool Primitive:**
   * Dựng môi trường Docker có volume mapping vào mã nguồn dự án.
   * Định nghĩa các tool cơ bản: `fs_read`, `fs_patch`, `terminal_exec`, `test_runner`.
2. **Giai đoạn 2 - Routing & State Graph Engine:**
   * Hiện thực hóa `GlobalDAGState` và thuật toán duyệt topological sort cho các batch chạy song song.
   * Viết logic `DynamicModelRouter` (chọn model dựa trên complexity score và domain).
3. **Giai đoạn 3 - Verifier & Closed-Loop Re-planning:**
   * Kết nối Verifier Gate: kiểm tra compile syntax và unit test sau mỗi lần code được sinh ra.
   * Viết logic phản hồi (Feedback Prompt) gom log lỗi gửi ngược lại cho Planner để tái cấu trúc DAG khi có node fail.
4. **Giai đoạn 4 - Full-Stack Real-Time Dashboard:**
   * Dựng backend WebSocket trung tâm phát stream event của pipeline.
   * Dựng frontend Next.js với React Flow để trực quan hóa đồ thị DAG và Xterm.js để render terminal output.
```

Tài liệu đã khái quát hóa toàn bộ logic và cung cấp đầy đủ stack kỹ thuật cho cả Backend, Engine lẫn UI/UX Dashboard. Bạn có thể lưu trữ và sử dụng trực tiếp bản thiết kế này làm tài liệu kỹ thuật chuẩn (Technical Specification) để tiến hành lập trình dự án.