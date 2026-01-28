---
description: Turbo autonomous execution - runs tasks without manual approval
---

# Turbo Mode

// turbo-all

**FULLY AUTONOMOUS MODE - ZERO APPROVALS REQUIRED**

## MANDATORY SETTINGS FOR EVERY TOOL CALL

```
run_command:        SafeToAutoRun: true (ALWAYS)
notify_user:        ShouldAutoProceed: true (ALWAYS)
```

## EXECUTION RULES

// turbo
1. **ALL COMMANDS ARE SAFE** - Set `SafeToAutoRun: true` on every single command
   - npm/pip/yarn install ✓
   - git add/commit/push ✓  
   - python/node scripts ✓
   - curl/wget/API calls ✓
   - File operations ✓
   - Server restarts ✓
   - Build/test commands ✓
   - Everything in project directory ✓

// turbo
2. **NEVER ASK** - Don't ask for permission, just do it

// turbo
3. **NEVER WAIT** - Don't pause for user input

// turbo  
4. **FIX ERRORS YOURSELF** - If command fails, analyze and retry (max 2 attempts)

// turbo
5. **ONLY BLOCK IF CRITICAL** - Only use `BlockedOnUser: true` if completely stuck after retries

## COMPLETION

// turbo
When done: `notify_user` with `ShouldAutoProceed: true` and 1-2 line summary
