# Model Download & Provider Discovery - Test Plan

## Purpose
Verify that the model download system and dynamic provider discovery work correctly with zero caching.

## Prerequisites
- Digital Article backend and frontend running
- No API keys set initially
- Ollama installed and running locally

---

## Test 1: Initial Provider Detection (No API Keys)

**Steps:**
1. Start backend: `da-backend`
2. Start frontend: `da-frontend`
3. Open Settings modal

**Expected:**
- ✅ Provider list shows: Ollama, LMStudio (if installed), HuggingFace, MLX
- ✅ OpenAI and Anthropic NOT in list (no API keys)
- ✅ Loading is fast (providers without models)
- ✅ Selecting Ollama loads model list

**Verify:**
```bash
# Check backend logs for:
"🔍 Detecting available LLM providers..."
"🏁 Found X available providers"
```

---

## Test 2: Add OpenAI API Key - Dynamic Provider Appearance

**Steps:**
1. Open Settings → Advanced Settings
2. Enter OpenAI API key: `sk-test-xxx`
3. Click "Save" button

**Expected:**
- ✅ Toast notification: "openai API key saved"
- ✅ Provider list **automatically refreshes**
- ✅ OpenAI **appears** in provider dropdown
- ✅ Can select OpenAI immediately
- ✅ OpenAI models load automatically

**Verify:**
```bash
# Backend logs should show:
"🔍 Detecting available LLM providers..."  # Refresh call
# Frontend network tab:
GET /api/llm/providers  # Provider refresh
GET /api/llm/providers/openai/models  # Model fetch
```

---

## Test 3: Add Anthropic API Key While OpenAI Selected

**Steps:**
1. Keep OpenAI selected from Test 2
2. Add Anthropic API key: `sk-ant-xxx`
3. Click "Save" button

**Expected:**
- ✅ Toast notification: "anthropic API key saved"
- ✅ Provider list refreshes
- ✅ Anthropic appears in dropdown
- ✅ OpenAI stays selected (not switched)
- ✅ OpenAI models still loaded

**Verify:**
```bash
# Only provider list refreshes, NOT models (OpenAI still selected)
GET /api/llm/providers  # ✅
GET /api/llm/providers/openai/models  # ❌ Should NOT fetch again
```

---

## Test 4: Remote Ollama Base URL

**Steps:**
1. Select "Ollama" provider
2. Note current models (local Ollama)
3. Open Advanced Settings → Base URLs
4. Change Ollama URL to: `http://192.168.1.100:11434` (remote server)
5. Click blue "Update" button

**Expected:**
- ✅ Loading spinner on Update button
- ✅ Provider list refreshes (checks connection)
- ✅ Model list refreshes with remote server's models
- ✅ Model dropdown updates to show remote models
- ✅ Can select and use remote models

**Verify:**
```bash
# Backend logs:
"🔍 Detecting available LLM providers..."
"🔍 Fetching models for ollama..."
# Network tab:
GET /api/llm/providers
GET /api/llm/providers/ollama/models?base_url=http://192.168.1.100:11434
```

---

## Test 5: Download Model (Ollama)

**Steps:**
1. Select Ollama provider (local or remote)
2. Enter model name: `gemma3:1b`
3. Click "Download"
4. Wait for download to complete

**Expected:**
- ✅ "Active Download" section appears at top
- ✅ Progress bar updates in real-time
- ✅ Can close modal - download continues
- ✅ Reopen modal - progress still visible
- ✅ Toast notification: "Model gemma3:1b is ready to use"
- ✅ Model list **automatically refreshes**
- ✅ `gemma3:1b` appears in dropdown

**Verify:**
```bash
# Backend logs:
POST /api/models/pull  # SSE stream
"🔍 Fetching models for ollama..."  # Auto-refresh after complete
# Frontend:
Event: model-download-complete
GET /api/llm/providers/ollama/models
```

---

## Test 6: Download HuggingFace Model with Auth Token

**Steps:**
1. Select HuggingFace provider
2. Enter model: `meta-llama/Llama-2-7b-hf`
3. Enter auth token: `hf_xxx`
4. Click "Download"
5. Wait for completion

**Expected:**
- ✅ Download starts
- ✅ Progress visible in Active Download section
- ✅ Toast: "Model meta-llama/Llama-2-7b-hf is ready to use"
- ✅ Model appears in HuggingFace dropdown
- ✅ Can select and use immediately

---

## Test 7: Switch Provider During Download

**Steps:**
1. Start downloading Ollama model (large, e.g., `llama3:70b`)
2. While downloading, switch to "OpenAI" provider
3. Browse OpenAI models
4. Switch back to Ollama

**Expected:**
- ✅ Active Download section **always visible** regardless of selected provider
- ✅ Can browse OpenAI models while Ollama downloads
- ✅ Progress continues updating
- ✅ Switch back to Ollama - download still running
- ✅ Completion triggers model refresh only for Ollama

---

## Test 8: Modal Close/Reopen During Download

**Steps:**
1. Start downloading model
2. Close Settings modal
3. Wait 10 seconds
4. Reopen Settings modal

**Expected:**
- ✅ Download continues in background (context at App level)
- ✅ Active Download section shows current progress
- ✅ Progress has advanced from when modal was closed
- ✅ Can cancel download
- ✅ Completion triggers refresh even if modal closed

---

## Test 9: Cancel Download

**Steps:**
1. Start downloading large model
2. Wait for progress to reach ~20%
3. Click "Cancel" button in Active Download section

**Expected:**
- ✅ Download stops immediately
- ✅ Toast: "Download cancelled"
- ✅ Active Download section disappears
- ✅ Can start new download
- ✅ Model NOT added to dropdown (incomplete)

---

## Test 10: No Caching Verification

**Steps:**
1. Open Settings
2. Note provider list
3. Close Settings
4. **Externally**: Add new Ollama model via CLI: `ollama pull qwen3:4b`
5. Reopen Settings
6. Select Ollama

**Expected:**
- ✅ Provider list fetched fresh (no cache)
- ✅ Model list shows newly pulled `qwen3:4b`
- ✅ No need to click refresh

**Verify:**
```bash
# Each modal open triggers fresh API call
GET /api/llm/providers
GET /api/llm/providers/ollama/models
```

---

## Test 11: Delete API Key - Provider Disappears

**Steps:**
1. Open Settings (OpenAI in provider list from Test 2)
2. Advanced Settings → OpenAI API key → Click "Clear"
3. Confirm deletion

**Expected:**
- ⚠️ **Current behavior**: Provider list NOT refreshed automatically
- ✅ **Workaround**: Close and reopen Settings
- ✅ OpenAI no longer in provider list

**Note:** Could add `refreshProviders()` to `handleDeleteApiKey()` for better UX.

---

## Test 12: Invalid Base URL

**Steps:**
1. Select Ollama
2. Change base URL to: `http://invalid-server:11434`
3. Click "Update" button

**Expected:**
- ✅ Button shows loading spinner
- ✅ Eventually times out or shows error
- ✅ Model list becomes empty or shows error
- ✅ Provider might disappear from list (connection failed)

---

## Performance Tests

### Test P1: Fast Provider List Loading
**Steps:**
1. Open Settings modal

**Expected:**
- ✅ Provider list loads in < 500ms
- ✅ Uses `include_models=False` (fast)
- ✅ No model data fetched initially

### Test P2: Model List Lazy Loading
**Steps:**
1. Open Settings
2. Select provider

**Expected:**
- ✅ Models load after provider selected (not before)
- ✅ Shows "(loading...)" indicator
- ✅ Dropdown disabled during load

---

## Edge Cases

### E1: Rapid Provider Switching
**Steps:**
1. Quickly switch: Ollama → OpenAI → Anthropic → Ollama

**Expected:**
- ✅ Each switch triggers model fetch
- ✅ No race conditions (latest selected wins)
- ✅ Loading states clear properly

### E2: Multiple Base URL Updates
**Steps:**
1. Change Ollama URL
2. Click Update
3. Immediately change URL again
4. Click Update again

**Expected:**
- ✅ Second update cancels/overrides first
- ✅ Final URL is used
- ✅ No duplicate requests

---

## Verification Checklist

After running all tests, verify:

- [ ] **Zero caching**: Every modal open fetches fresh providers
- [ ] **Dynamic discovery**: API keys make providers appear immediately
- [ ] **Base URL updates**: Refresh button works, fetches from new URL
- [ ] **Download integration**: Completed downloads refresh model list
- [ ] **Persistent state**: Downloads continue with modal closed
- [ ] **Always visible**: Active Download section shown regardless of tab/provider
- [ ] **No race conditions**: Rapid actions handled correctly
- [ ] **Performance**: Fast provider list, lazy model loading
- [ ] **Error handling**: Invalid URLs/keys don't break UI

---

## Known Issues / Future Improvements

1. **Delete API Key**: Should auto-refresh provider list (currently requires modal reopen)
2. **Network errors**: Could show better error messages in UI
3. **Base URL validation**: Could validate URL format before calling API
4. **Model list errors**: Could show inline error instead of empty dropdown

---

## AbstractCore Integration Points

All these methods are called fresh (no caching):

| Frontend Action | Backend Endpoint | AbstractCore Method |
|----------------|------------------|---------------------|
| Open Settings | `GET /providers` | `get_all_providers_with_models(include_models=False)` |
| Save API Key | `GET /providers` | `get_all_providers_with_models(include_models=False)` |
| Select Provider | `GET /providers/{provider}/models` | `create_llm().list_available_models()` |
| Update Base URL | `GET /providers` + `/providers/{provider}/models` | Both methods above |
| Download Complete | `GET /providers/{provider}/models` | `create_llm().list_available_models()` |

**Key**: Every call goes to AbstractCore fresh - **zero caching** at our level.
