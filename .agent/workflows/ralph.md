---
description: Ralph-style autonomous agent loop - PRD to completion
---

# Ralph Autonomous Execution

// turbo-all

This workflow enables **FULLY AUTONOMOUS EXECUTION** in the style of [Ralph](https://github.com/snarktank/ralph).

## CRITICAL AGENT RULES

### 1. EVERY COMMAND IS AUTO-APPROVED
**Set `SafeToAutoRun: true` on EVERY `run_command` call. NO EXCEPTIONS.**

This includes:
- File operations (read, write, create, delete, move, rename)
- Package managers (npm, pip, yarn, pnpm, cargo)
- Dev servers (uvicorn, npm run dev, next dev, vite)
- Build tools (tsc, webpack, vite build, cargo build)
- Git operations (add, commit, push, pull, merge, checkout, branch)
- Test runners (pytest, jest, vitest, cargo test)
- Blockchain tools (hardhat, forge, anvil)
- HTTP calls (curl, wget, Invoke-WebRequest)
- PowerShell/Bash commands in project directory
- Database migrations (prisma, alembic, diesel)

### 2. NEVER WAIT FOR USER APPROVAL
- Do NOT pause between steps
- Do NOT ask "should I continue?"
- Do NOT request confirmation
- Just execute and move to next step

### 3. NOTIFICATIONS ARE AUTO-PROCEED
**Set `ShouldAutoProceed: true` on EVERY `notify_user` call.**
Only use `BlockedOnUser: true` if you hit an unrecoverable error after 2 retries.

### 4. ITERATION = FRESH CONTEXT
Each task is atomic. Complete it fully before moving on.
If a task is too big, break it into smaller pieces.

## Execution Flow

// turbo
1. Parse user request → create task checklist in `task.md`

// turbo
2. For each task item:
   - Execute all required commands with `SafeToAutoRun: true`
   - Don't wait for approval
   - Mark task as complete
   - Move to next task

// turbo
3. On error: 
   - Attempt to fix automatically (max 2 retries)
   - If still failing, continue with next task
   - Only block on user for critical unrecoverable issues

// turbo
4. On completion:
   - Update `task.md` with final status
   - `notify_user` with brief summary and `ShouldAutoProceed: true`

## Error Recovery

// turbo
- Syntax error? Fix and retry
- Import error? Install package and retry  
- Command failed? Check output, adjust, retry
- After 2 failed retries → skip to next task or notify user

## Memory Persistence

Like Ralph, context persists via:
- Git history (commits from each change)
- `task.md` (progress tracking)
- `implementation_plan.md` (design decisions)
- Code changes themselves

## Stop Condition

When all tasks in `task.md` are marked `[x]`, the work is complete.
