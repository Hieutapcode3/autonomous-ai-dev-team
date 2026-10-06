# Autonomous AI Dev Team — Phân tích & Định hướng phát triển

> Repository: `https://github.com/Hieutapcode3/autonomous-ai-dev-team`
>
> Mục tiêu đánh giá: xác định repo có phù hợp làm nền tảng cho hệ thống **Leader điều phối nhiều AI model/agent, tự chọn model theo task, thực thi, kiểm thử và tự sửa lỗi** hay không.

---

## 1. Executive Summary

`autonomous-ai-dev-team` là một prototype khá sát với ý tưởng **AI Development Team**:

```text
User Request
    ↓
Team Leader / Planner
    ↓
Task Decomposition
    ↓
Model Router
    ↓
Multiple AI Models / Agents
    ↓
Execution
    ↓
Verification
    ↓
PASS → Done
FAIL → Replanning → Retry
```

Điểm nổi bật nhất của repo là nó đã đưa vào kiến trúc:

- Team Leader / Planner
- Task DAG
- Dynamic Model Router
- Complexity-aware routing
- Replanning khi task thất bại
- Verification / Quality Gate
- Sandbox abstraction
- LLM abstraction
- Dashboard / event flow

### Kết luận

Repo **nên được xem là foundation/prototype**, không phải production-ready autonomous software engineer.

Đánh giá tổng thể:

| Hạng mục | Đánh giá |
|---|---:|
| Multi-agent concept | ⭐⭐⭐⭐ |
| Leader concept | ⭐⭐⭐⭐ |
| Dynamic model routing | ⭐⭐⭐⭐ |
| DAG | ⭐⭐⭐⭐ |
| Replanning | ⭐⭐⭐⭐ |
| Quality Gate concept | ⭐⭐⭐⭐ |
| Multi-provider architecture | ⭐⭐⭐⭐ |
| Tool execution | ⭐⭐ |
| Autonomous coding | ⭐⭐ |
| Intelligent task decomposition | ⭐⭐ |
| Intelligent model selection | ⭐⭐ |
| Production sandbox | ⭐ |
| Unity support | ⭐ |

**Prototype / research foundation: ~6.5/10**

**Production autonomous software engineer: ~3.5–4/10**

---

# 2. Repo đang giải quyết bài toán gì?

Ý tưởng trung tâm là biến một yêu cầu phần mềm thành một chuỗi task được điều phối bởi Leader.

Kiến trúc khái niệm:

```text
                    USER REQUEST
                         │
                         ▼
                  ┌─────────────┐
                  │ TEAM LEADER │
                  │   Planner   │
                  └──────┬──────┘
                         │
                  Decompose Task
                         │
                         ▼
                 ┌──────────────┐
                 │ MODEL ROUTER │
                 └──────┬───────┘
                        │
        ┌───────────────┼────────────────┐
        ▼               ▼                ▼
     Analysis        Coding           Testing
        │               │                │
     Model A          Model B          Model C
        │               │                │
        └───────────────┼────────────────┘
                        ▼
                  TOOL / SANDBOX
                        │
                        ▼
                    VERIFIER
                   /         \
                PASS         FAIL
                 │             │
               DONE       REPLANNER
                              │
                              ▼
                            ROUTER
```

Điểm quan trọng: repo không chỉ muốn chạy nhiều agent song song, mà có ý tưởng **chọn model phù hợp cho từng loại task**.

---

# 3. So sánh với yêu cầu của hệ thống mong muốn

Mục tiêu mong muốn:

> “Một Leader điều phối nhiều model AI khác nhau và chọn đúng model cho từng công việc.”

Repo đáp ứng được phần lớn ý tưởng ở mức kiến trúc:

```text
Leader
  ↓
Task
  ↓
Router
  ↓
Model phù hợp
  ↓
Execute
  ↓
Verify
```

Đây là điểm khiến repo phù hợp để làm base hơn các framework chỉ tập trung vào việc giúp **một agent lập kế hoạch và sử dụng tools tốt hơn**.

---

# 4. Kiến trúc hiện tại

Các thành phần chính có thể hình dung như sau:

```text
backend/
├── planner.py
├── router.py
├── sandbox.py
├── verifier.py
├── llm.py
├── orchestrator.py
├── github_service.py
├── schemas.py
└── tests/
```

Vai trò:

| Component | Vai trò |
|---|---|
| `planner.py` | Phân rã objective, tạo task/DAG, replanning |
| `router.py` | Chọn model theo domain/complexity/cost |
| `sandbox.py` | File system + terminal + test abstraction |
| `verifier.py` | Syntax/test/quality checks |
| `llm.py` | LLM provider abstraction |
| `orchestrator.py` | Điều phối execution |
| `github_service.py` | GitHub integration |
| `schemas.py` | Data models / task state |

---

# 5. Model Router — điểm mạnh nhất

Router là phần gần nhất với yêu cầu **Leader chọn model theo task**.

Một task có thể chứa:

```text
domain
complexity
required_tools
cost constraint
context requirements
```

Router sau đó chọn model.

Ví dụ logic hiện tại có dạng:

```text
Architecture
    complexity >= 8
        → Claude Opus

Architecture
    complexity < 8
        → Claude Sonnet

Implementation
    complexity >= 7
        → Claude Sonnet

Implementation
    complexity 4–6
        → GPT-4o

Implementation
    complexity <= 3
        → GPT-4o-mini

Utility
        → GPT-4o-mini
```

Ngoài model, hệ thống còn có thể lưu:

```text
assigned_model
assigned_agent
routing_rationale
complexity
cost_usd
execution_time_ms
```

### Đánh giá

Design này **nên được giữ lại**.

---

# 6. Hạn chế của Model Router

Router hiện tại chủ yếu là **rule-based**, chưa phải intelligent model selection.

Hiện tại gần với:

```text
Task
 ↓
Classification
 ↓
if/else rules
 ↓
Model
```

Hệ thống mong muốn nên tiến tới:

```text
Task
 ↓
Task Analyzer
 ├── reasoning difficulty
 ├── coding difficulty
 ├── context size
 ├── language
 ├── repository familiarity
 ├── tool requirements
 ├── latency requirement
 ├── cost
 ├── risk
 └── historical success rate
 ↓
Model Selection Engine
 ↓
Best Model / Agent
```

### Model Router v2 nên có

```text
Model Capability Registry
Model Cost Registry
Model Context Registry
Model Tool Capability
Historical Success Rate
Task Difficulty
Repository Context
Latency
Budget
Failure History
```

Sau đó tính:

```text
model_score =
    capability_score
  + task_fit_score
  + historical_success
  + context_fit
  - cost_penalty
  - latency_penalty
  - failure_penalty
```

---

# 7. Planner / Leader — điểm yếu lớn

Đây là phần cần sửa nhiều nhất.

Ý tưởng kiến trúc là:

```text
Requirement
 ↓
Leader
 ↓
Understand requirement
 ↓
Generate DAG
```

Nhưng implementation hiện tại có xu hướng dùng pipeline cố định:

```text
Architecture
     ↓
Implementation
     ↓
Unit Tests
     ↓
Quality Gate
```

Dependency cũng tương đối cố định.

Điều này có nghĩa:

> Planner hiện tại giống một **workflow template engine** hơn là một Leader có khả năng tự phân tích requirement.

---

# 8. Leader mà hệ thống thực sự cần

Ví dụ requirement:

> “Tạo hệ thống login bằng Google OAuth, PostgreSQL, Redis và React frontend.”

Leader nên tạo:

```text
                    Requirement
                         │
                         ▼
                    Architect
                         │
          ┌──────────────┼───────────────┐
          ▼              ▼               ▼
     DB Schema       OAuth Design    API Contract
          │              │               │
          └──────────────┼───────────────┘
                         ▼
                    Backend API
                         │
              ┌──────────┴─────────┐
              ▼                    ▼
          Redis Cache          Frontend
              │                    │
              └──────────┬─────────┘
                         ▼
                    Integration
                         │
                         ▼
                      Testing
                         │
                         ▼
                      Review
```

Không nên ép mọi project vào:

```text
Architecture → Coding → Testing → Verification
```

---

# 9. Replanning — ý tưởng tốt

Repo có closed-loop:

```text
Execute
   ↓
Verify
   ↓
PASS → Done

FAIL
 ↓
Error Trace
 ↓
Replanner
 ↓
Create Fix Task
 ↓
Router
 ↓
Execute
 ↓
Verify
```

Đây là một trong những phần đáng giữ.

---

# 10. Hạn chế của Replanner

Replanner hiện tại chưa thực sự phân tích root cause sâu.

Flow thực tế gần hơn:

```text
Task Failed
    ↓
Increase complexity
    ↓
Create Fix Task
    ↓
Retry
```

Hệ thống mong muốn:

```text
Failure
   ↓
Failure Analyzer
   ↓
Root Cause Classification
   ├── compile error
   ├── architecture error
   ├── API error
   ├── test error
   ├── environment error
   └── model mistake
   ↓
Recovery Strategy
   ↓
Choose model again
   ↓
Modify DAG
   ↓
Retry
```

Đặc biệt:

```text
Model A fails twice
        ↓
Router should consider Model B
```

Đây là tính năng quan trọng cho AI Dev Team.

---

# 11. Verification / Quality Gate

Repo có ý tưởng rất đúng:

> Không tin tuyệt đối vào output của LLM; phải có verification.

Các kiểu kiểm tra có thể bao gồm:

```text
AST / syntax
JSON validation
pytest
generic validation
```

Flow:

```text
AI says:
"Code is correct."

        ↓

Verifier
        ↓

PASS / FAIL
```

Đây là design nên giữ.

---

# 12. Hạn chế của Quality Gate

README/kiến trúc hướng tới:

```text
Syntax
Build
Compile
Tests
```

nhưng implementation hiện tại chưa phải một universal build/test engine.

Một số loại file/project có thể chỉ được kiểm tra generic thay vì compile/build thực sự.

Ví dụ production system cần:

```text
TypeScript
    → tsc

C#
    → dotnet build

Python
    → pytest

C++
    → cmake + compiler

Unity
    → Unity batchmode build

Android
    → Gradle

Web
    → npm test / npm build
```

---

# 13. Vấn đề đặc biệt nếu dùng cho Unity

Với Unity, Quality Gate nên được mở rộng thành:

```text
Unity Project
       │
       ▼
Unity Compiler
       │
       ▼
Assembly Compilation
       │
       ▼
Unity Test Framework
       │
       ▼
PlayMode Tests
       │
       ▼
Build Android/Windows
       │
       ▼
PASS / FAIL
```

Ví dụ command concept:

```text
Unity.exe
  -batchmode
  -quit
  -projectPath <project>
  -executeMethod BuildScript.Build
```

Sau đó thu thập:

```text
exit code
Unity Editor.log
compiler errors
test results
build result
```

và gửi lại cho:

```text
Failure Analyzer
        ↓
Replanner
```

---

# 14. Agent Execution — điểm yếu lớn

Hiện tại execution có xu hướng:

```text
LLM
 ↓
Generate code / files
 ↓
Write files
 ↓
Verifier
```

Trong khi một coding agent thực sự nên:

```text
LLM
 ↓
Inspect repository
 ↓
Read files
 ↓
Search symbols
 ↓
Modify files
 ↓
Run command
 ↓
Read error
 ↓
Modify
 ↓
Run tests
 ↓
Inspect failure
 ↓
Fix
 ↓
Repeat
```

Đây là khác biệt giữa:

- LLM code generator
- autonomous coding agent

Repo có sandbox abstraction khá tốt để phát triển tiếp, nhưng agent loop chưa đủ sâu.

---

# 15. Tool System nên được nâng cấp

Sandbox đã có những abstraction kiểu:

```text
fs_read
fs_write
fs_patch
fs_list
terminal_exec
test_runner
```

Đây là nền tảng tốt.

Nhưng autonomous agent cần policy rõ ràng:

```text
File access
Terminal
Git
Build
Test
Search
Package manager
Network
Browser (optional)
```

và mỗi agent cần được cấp tool theo task:

```text
Researcher
    → read/search/web

Architect
    → read/search

Coder
    → read/write/patch/terminal

QA
    → read/terminal/test

DevOps
    → terminal/git/build
```

---

# 16. Agent Provider Architecture nên thay đổi

Một mục tiêu quan trọng của hệ thống mới là không khóa Leader vào một API duy nhất.

Nên có abstraction:

```text
AgentProvider
│
├── ClaudeCodeProvider
├── CodexCLIProvider
├── GeminiCLIProvider
├── OpenAIProvider
├── DeepSeekProvider
├── OllamaProvider
└── GenericAPIProvider
```

Leader chỉ cần yêu cầu:

```json
{
  "task": "Implement authentication",
  "agent_role": "coder",
  "model": "codex",
  "workspace": "...",
  "tools": ["filesystem", "terminal", "git"]
}
```

Provider chịu trách nhiệm thực thi model/agent tương ứng.

---

# 17. Đây là điểm khác biệt quan trọng

Không nên chỉ xây:

```text
Multi-model API orchestration
```

Mục tiêu nên là:

```text
Multi-agent
+
Multi-model
+
Agent CLI orchestration
+
Tool execution
+
Verification
+
Replanning
```

Ví dụ:

```text
Research
    → Claude Sonnet

Architecture
    → Claude Opus

Coding
    → Codex

Large repository analysis
    → Gemini

Cheap utility
    → DeepSeek / small model

Code review
    → Claude Opus

Unity build/test
    → Verification Agent
```

Đây mới thực sự là:

> Autonomous AI Development Team.

---

# 18. GitHub workflow nên nâng cấp

Repo có GitHub integration, nhưng production workflow nên là:

```text
Issue / User Request
        ↓
Leader
        ↓
Task DAG
        ↓
Dedicated Git Worktree
        ↓
Agent executes
        ↓
Commit
        ↓
Pull Request
        ↓
CI
        ↓
Review Agent
        ↓
Fix
        ↓
CI again
        ↓
Merge
```

Mỗi task hoặc nhóm task nên có workspace/worktree riêng để tránh agent phá trạng thái của agent khác.

---

# 19. Security / Sandbox

Autonomous coding agent có quyền chạy command là rủi ro cao.

Không nên chỉ dựa vào:

```text
subprocess
+
path checking
```

Production cần:

```text
Docker / isolated VM / Firecracker
+
CPU limit
+
RAM limit
+
timeout
+
filesystem isolation
+
network policy
+
process limit
+
secret isolation
```

Đặc biệt không truyền API keys vào sandbox không kiểm soát.

---

# 20. Kiến trúc đề xuất cho v2

```text
                         USER
                          │
                          ▼
                 ┌─────────────────┐
                 │   TEAM LEADER   │
                 │  Master Agent   │
                 └────────┬────────┘
                          │
                          ▼
                ┌────────────────────┐
                │ TASK ANALYZER      │
                │                    │
                │ domain             │
                │ complexity         │
                │ context size       │
                │ dependencies       │
                │ tools              │
                │ risk               │
                └─────────┬──────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ TASK DAG        │
                 └────────┬────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │ MODEL ROUTER    │
                 └────────┬────────┘
                          │
          ┌───────────────┼─────────────────┐
          │               │                 │
          ▼               ▼                 ▼
       Claude           Codex            Gemini
       Opus             CLI              Pro
          │               │                 │
          ▼               ▼                 ▼
       Architect       Coder             Researcher
          │               │                 │
          └───────────────┼─────────────────┘
                          ▼
                   TOOL EXECUTOR
                          │
          ┌───────────────┼─────────────────┐
          ▼               ▼                 ▼
       Filesystem       Terminal          Git
          │               │                 │
          └───────────────┼─────────────────┘
                          ▼
                    BUILD / TEST
                          │
                    ┌─────┴─────┐
                    ▼           ▼
                  PASS         FAIL
                    │           │
                    ▼           ▼
                  DONE       ERROR ANALYZER
                                │
                                ▼
                           REPLANNER
                                │
                                ▼
                           MODEL ROUTER
```

---

# 21. Các module nên xây

## Phase 1 — Core orchestration

- [ ] Leader Agent
- [ ] Task Analyzer
- [ ] Dynamic Task DAG
- [ ] Task state machine
- [ ] Dependency management
- [ ] Persistent execution state

## Phase 2 — Model Router

- [ ] Model Registry
- [ ] Capability Registry
- [ ] Cost Registry
- [ ] Context-window Registry
- [ ] Tool compatibility
- [ ] Historical success score
- [ ] Dynamic routing
- [ ] Fallback model
- [ ] Model switching after repeated failures

## Phase 3 — Agent Providers

- [ ] Claude provider
- [ ] Codex provider
- [ ] Gemini provider
- [ ] OpenAI provider
- [ ] DeepSeek provider
- [ ] Local model provider

## Phase 4 — Coding Agent

- [ ] Repository inspection
- [ ] File search
- [ ] Symbol search
- [ ] Read/write/patch
- [ ] Terminal execution
- [ ] Git operations
- [ ] Build
- [ ] Test
- [ ] Error analysis
- [ ] Iterative fix loop

## Phase 5 — Verification

- [ ] Language-specific compiler
- [ ] Unit test
- [ ] Integration test
- [ ] Build test
- [ ] Static analysis
- [ ] Security checks
- [ ] Regression tests

## Phase 6 — Replanning

- [ ] Root-cause analysis
- [ ] Failure classification
- [ ] Recovery strategy
- [ ] DAG modification
- [ ] Model switching
- [ ] Retry budget
- [ ] Escalation to stronger model

## Phase 7 — Git workflow

- [ ] Git worktree
- [ ] Branch per task
- [ ] Automatic commit
- [ ] PR generation
- [ ] CI
- [ ] Review agent
- [ ] Auto-fix
- [ ] Merge policy

## Phase 8 — Observability

- [ ] Task timeline
- [ ] Model usage
- [ ] Token usage
- [ ] Cost
- [ ] Latency
- [ ] Success rate
- [ ] Failure reason
- [ ] Model comparison
- [ ] Agent trace

---

# 22. Model Router v2 — đề xuất cụ thể

Mỗi model nên có registry:

```json
{
  "id": "claude-opus",
  "capabilities": [
    "architecture",
    "reasoning",
    "code-review",
    "complex-coding"
  ],
  "context_window": 200000,
  "cost_level": 5,
  "latency_level": 3,
  "tool_support": [
    "filesystem",
    "terminal",
    "git"
  ]
}
```

Task cũng được chuẩn hóa:

```json
{
  "id": "TASK-123",
  "domain": "coding",
  "complexity": 8,
  "risk": 7,
  "context_size": 50000,
  "required_tools": [
    "filesystem",
    "terminal",
    "git"
  ]
}
```

Router tính:

```text
Task ↔ Model Compatibility
```

và chọn:

```text
Best Model
+
Fallback Model
+
Reason
```

---

# 23. Cơ chế Feedback Loop nên có

Router không nên cố định mãi.

Sau mỗi task:

```text
Task
 ↓
Model A
 ↓
Result
 ↓
Quality
 ↓
Store Metrics
```

Ví dụ:

```text
Claude Sonnet
Coding:
success = 87%
avg cost = $0.08
avg time = 41s

Codex
Coding:
success = 94%
avg cost = $0.05
avg time = 35s
```

Router có thể học:

```text
Coding + TypeScript
→ ưu tiên Codex

Architecture + complex
→ ưu tiên Claude Opus

Large context research
→ ưu tiên Gemini
```

Đây là bước biến:

```text
Rule-based Router
```

thành:

```text
Learning / Adaptive Router
```

---

# 24. Test strategy quan trọng nhất

Không nên chỉ test từng module.

Cần benchmark toàn hệ thống.

Ví dụ:

```text
Benchmark #1
Simple CRUD

Benchmark #2
Authentication

Benchmark #3
REST API

Benchmark #4
React frontend

Benchmark #5
Unity feature

Benchmark #6
Existing repo bug fix

Benchmark #7
Large refactor
```

Mỗi benchmark đo:

```text
Task success
Code correctness
Test pass rate
Build success
Cost
Time
Number of retries
Model switches
Human intervention
```

Metric quan trọng nhất:

```text
% tasks completed without human intervention
```

---

# 25. Nếu dùng cho Unity

Đây là hướng rất phù hợp với project Unity.

Nên có specialized agents:

```text
Unity Leader
│
├── Unity Architect
├── C# Coder
├── Unity Scene Agent
├── Asset Agent
├── Shader Agent
├── UI Agent
├── Test Agent
└── Build Agent
```

Model routing:

```text
Game architecture
    → Claude Opus

C# implementation
    → Codex / strong coding model

Large Unity project analysis
    → Gemini / large-context model

Code review
    → Claude

Build verification
    → Unity Build Agent

PlayMode tests
    → Unity Test Agent
```

Với project Unity lớn, nên tích hợp thêm project indexing/code graph để Leader không phải gửi toàn bộ repository vào context mỗi lần.

---

# 26. Đề xuất roadmap

## MVP

```text
Leader
  ↓
Task Analyzer
  ↓
DAG
  ↓
Router
  ↓
Claude / Codex
  ↓
Sandbox
  ↓
Build/Test
  ↓
Verifier
```

## V1

Thêm:

```text
Replanner
Model fallback
Git worktree
PR
CI
Review Agent
```

## V2

Thêm:

```text
Adaptive Model Router
Historical performance
Cost optimization
Agent memory
Repository knowledge graph
Long-running tasks
Parallel execution
```

## V3

Hướng tới:

```text
User
 ↓
High-level requirement
 ↓
Autonomous Dev Team
 ↓
Research
 ↓
Architecture
 ↓
Implementation
 ↓
Testing
 ↓
Review
 ↓
Fix
 ↓
CI
 ↓
PR
 ↓
Human approval
```

---

# 27. Quyết định cuối cùng

### Có nên fork repo này?

**Có.**

### Có nên dùng nguyên bản?

**Không.**

### Có nên lấy kiến trúc làm foundation?

**Có, rất phù hợp.**

### Phần nên giữ nguyên ý tưởng

```text
Planner
Router
DAG
Verifier
Replanner
Sandbox
LLM abstraction
Dashboard
```

### Phần cần redesign

```text
Leader intelligence
Task decomposition
Model selection
Agent execution loop
Tool system
Failure analysis
Replanning
Build/test
Git workflow
Sandbox security
```

---

# 28. Kiến trúc mục tiêu cuối cùng

Hệ thống cuối cùng nên đạt:

```text
                         USER
                          │
                          ▼
                  ┌──────────────┐
                  │ TEAM LEADER  │
                  └──────┬───────┘
                         │
                         ▼
                  REQUIREMENT
                    ANALYZER
                         │
                         ▼
                    TASK DAG
                         │
                         ▼
                 INTELLIGENT ROUTER
                         │
        ┌────────────────┼─────────────────┐
        ▼                ▼                 ▼
     CLAUDE            CODEX            GEMINI
        │                │                 │
     Research         Coding            Context
     Architect        Agent             Analysis
        │                │                 │
        └────────────────┼─────────────────┘
                         ▼
                  TOOL EXECUTION
                         │
                  ┌──────┼──────┐
                  ▼      ▼      ▼
                FILES  SHELL   GIT
                         │
                         ▼
                    BUILD/TEST
                         │
                    ┌────┴────┐
                    ▼         ▼
                  PASS       FAIL
                    │         │
                    ▼         ▼
                  REVIEW   FAILURE
                             ANALYZER
                                │
                                ▼
                           REPLANNER
                                │
                                ▼
                        MODEL RE-SELECTION
                                │
                                ▼
                              RETRY
                                │
                                ▼
                               PR
                                │
                                ▼
                              CI/CD
                                │
                                ▼
                              DONE
```

**Đây là kiến trúc nên hướng tới nếu mục tiêu cuối cùng là một “Leader AI” thực sự có khả năng điều phối Claude, Codex, Gemini và các coding agents khác nhau theo đúng loại công việc.**

---

## 29. Reference

- Repository: `https://github.com/Hieutapcode3/autonomous-ai-dev-team`
- Architecture focus: `planner.py`, `router.py`, `sandbox.py`, `verifier.py`, `llm.py`, `orchestrator.py`
- GitHub integration: `github_service.py`
- Data model / task state: `schemas.py`
- Tests: `backend/tests/test_system.py`

