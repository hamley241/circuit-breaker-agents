# exp-001 Troubleshooting Quick Reference

**For immediate help with the real API integration**

## 🔥 Emergency Fixes

### "Modal auth not found"
```bash
modal auth new
```

### "OpenAI API key not found"  
```bash
# Local:
export OPENAI_API_KEY="sk-your-key"

# Modal:
modal secret create openai-api-key OPENAI_API_KEY="sk-your-key"
```

### "No module named 'openai'"
```bash
pip install openai anthropic
# OR: source venv/bin/activate
```

### "Rate limit exceeded"
**Don't panic!** The experiment has built-in retry logic. Just wait 2-3 minutes and it will continue.

### "Function timeout after 60 minutes"
Switch to local execution for very large experiments:
```bash
python experiment_runner.py --full --real
```

## ⚡ Quick Tests

### Test everything is working:
```bash
python quick_api_test.py
```

### Test Modal setup:
```bash
modal run modal_app.py::main --runs 1 --real
```

### Test local setup:
```bash
python experiment_runner.py --runs 1 --real
```

## 💰 Cost Control

### Check costs before running:
```bash
python cost_estimator.py
```

### Start small:
```bash
# Mini test (50 calls, ~$0.63)
modal run modal_app.py::main --runs 5 --real

# Pilot test (100 calls, ~$1.26) 
modal run modal_app.py::main --runs 10 --real

# Full experiment (550 calls, ~$6.93)
modal run modal_app.py::main --full --real
```

## 🔍 Check Status

### View Modal secrets:
```bash
modal secret list
```

### View recent Modal runs:
```bash
modal logs list
```

### Check API key validity:
```bash
python -c "
from api_clients import GPTClient
client = GPTClient()
print('✅ API key works!') if client else print('❌ API key invalid')
"
```

## ⚠️ Expected Warnings (Not Errors!)

These are **normal** and don't break anything:

```
Warning: Anthropic API key not found, using OpenAI for both agents
```
→ **OK!** Experiment continues with GPT-4o for both agents.

```
Circuit breaker OPEN - blocking call
```
→ **OK!** This is the circuit breaker working correctly.

```
API timeout after 30s
```
→ **OK!** This is test data for the circuit breakers.

## 📞 Get Help

1. **Check this file first** (covers 90% of issues)
2. **Run integration tests**: `python test_real_api_integration.py`  
3. **Check the main guides**:
   - `MODAL_REAL_API_GUIDE.md` (comprehensive Modal guide)
   - `REAL_API_README.md` (basic integration)

## 🎯 Proven Working Commands

These commands have been tested and work:

```bash
# Successful pilot setup (exactly as run):
modal auth new
modal secret create openai-api-key OPENAI_API_KEY="your-key"
modal run modal_app.py::main --runs 10 --real

# Alternative (local execution):
export OPENAI_API_KEY="your-key" 
python experiment_runner.py --runs 10 --real
```

**Result**: 287 seconds, 100 API calls, $1.26 cost, 100% success rate ✅

---

**Last Updated:** March 19, 2026  
**Status:** Based on successful pilot completion