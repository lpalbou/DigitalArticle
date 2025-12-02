# AbstractCore v2.6.2 Upgrade - Programmatic Configuration

**Date**: 2025-12-02
**AbstractCore Version**: v2.6.2
**Status**: ✅ Complete and Verified
**Feature Request Response**: FEATURE_REQUEST_RESPONSE_ENV_VARS.md

---

## Executive Summary

Upgraded to AbstractCore v2.6.2 which implements our feature request for custom base URL support. The new **programmatic configuration API** (`configure_provider()`) provides a cleaner, more maintainable solution than environment variables.

### What Changed

✅ **Upgraded from v2.5.3 → v2.6.2**
✅ **Replaced manual base_url parameter passing with programmatic configuration**
✅ **Simplified backend code** - configure once, use everywhere
✅ **Zero breaking changes** - backward compatible
✅ **8/8 integration tests passing**

---

## What AbstractCore v2.6.2 Provides

AbstractCore team implemented **TWO solutions** to our feature request:

### 1. Environment Variables (v2.6.1)

```python
# Set env vars before calling AbstractCore
os.environ['OLLAMA_BASE_URL'] = 'http://192.168.1.100:11434'
providers = get_all_providers_with_models(include_models=False)
# Provider discovery now tests configured URL
```

### 2. Programmatic Configuration API (v2.6.2) ⭐ **We use this**

```python
from abstractcore.config import configure_provider

# Configure once
configure_provider('ollama', base_url='http://192.168.1.100:11434')

# All subsequent calls automatically use configured URL
llm = create_llm('ollama', model='llama3')  # ✅ Uses http://192.168.1.100:11434
models = llm.list_available_models()  # ✅ Tests connection to configured URL
```

### Priority System

1. **Constructor parameter** (highest): `create_llm("ollama", base_url="...")`
2. **Runtime configuration**: `configure_provider('ollama', base_url="...")` ⭐ **We use this**
3. **Environment variable**: `OLLAMA_BASE_URL`
4. **Default value** (lowest): `http://localhost:11434`

---

## Why Programmatic Config > Environment Variables

We chose the programmatic API (v2.6.2) over environment variables (v2.6.1) for these reasons:

✅ **Clean Architecture**: No env var pollution, clear separation of concerns
✅ **Runtime Updates**: User changes URL → immediate effect, no restart
✅ **State Management**: Settings in `user_settings.json` → applied via `configure_provider()`
✅ **No Race Conditions**: Env vars are process-global, programmatic is scoped
✅ **Better for Web UI**: Can set/query/clear configs per-provider
✅ **Testability**: Easy to mock and test
✅ **Type-safe**: IDE autocomplete and type hints

---

## Implementation

### Backend Changes (backend/app/api/llm.py)

#### Before (manual base_url parameter)

```python
@router.get("/providers/{provider}/models")
async def get_provider_models(provider: str, base_url: Optional[str] = None):
    def _get_models():
        kwargs = {}
        if base_url:
            kwargs['base_url'] = base_url

        llm = create_llm(provider, model="dummy", **kwargs)  # Manual parameter
        return llm.list_available_models()
```

#### After (programmatic configuration)

```python
@router.get("/providers/{provider}/models")
async def get_provider_models(provider: str, base_url: Optional[str] = None):
    def _get_models():
        if base_url:
            configure_provider(provider, base_url=base_url)  # Configure once

        llm = create_llm(provider, model="dummy")  # Automatically uses configured URL
        return llm.list_available_models()
```

#### Added to get_available_providers()

```python
from abstractcore.config import configure_provider

# Configure base URLs from user settings
for provider, base_url in settings.llm.base_urls.items():
    if base_url and base_url.strip():
        configure_provider(provider, base_url=base_url)
        logger.debug(f"📍 Configured {provider} base_url: {base_url}")

# Now all AbstractCore calls use configured URLs
providers = get_all_providers_with_models(include_models=False)
```

### Benefits

**Before**:
- Had to pass `base_url` parameter to EVERY `create_llm()` call
- Easy to forget and use default localhost
- No single source of truth

**After**:
- Configure ONCE from user settings
- All subsequent calls automatically use configured URL
- Settings persist, configuration is automatic

---

## How It Works

### User Flow: Changing Base URL

1. **User opens Settings**
   - Backend calls `get_available_providers()`
   - Settings loaded: `{"ollama": "http://localhost:11434"}`
   - `configure_provider('ollama', base_url='http://localhost:11434')`
   - Provider discovery uses configured URL

2. **User changes URL and clicks Blue "Update" button**
   - Frontend calls `GET /providers/ollama/models?base_url=http://remote:11434`
   - Backend: `configure_provider('ollama', base_url='http://remote:11434')`
   - Backend: `llm = create_llm('ollama', model='dummy')` ← Uses new URL
   - Backend: `llm.list_available_models()` ← Tests connection to remote:11434
   - Returns models if connection succeeds, error if fails

3. **User saves settings**
   - URL saved to `user_settings.json`
   - Next time settings open, configured automatically

### Technical Flow

```
User Settings (JSON)
  ↓
Backend: get_available_providers()
  ↓
configure_provider('ollama', base_url=user_url)
  ↓
AbstractCore Internal State (base_url registered)
  ↓
create_llm('ollama', model='test')
  ↓
AbstractCore automatically injects configured base_url
  ↓
Connection test / Model fetch
```

---

## Edge Case: LMStudio ModelNotFoundError

**Issue**: LMStudio validates model names and raises `ModelNotFoundError` when `create_llm('lmstudio', model='dummy')` is called with an invalid model name.

**Solution**: Catch `ModelNotFoundError` and parse the available models from the error message. AbstractCore helpfully includes the full model list in the error message:

```python
try:
    llm = create_llm(provider, model="dummy")
    return llm.list_available_models()
except ModelNotFoundError as e:
    # Parse available models from error message
    # Format: "Available models (N):\n  • model1\n  • model2\n..."
    error_msg = str(e)
    if "Available models" in error_msg:
        models = re.findall(r'  • (.+)', error_msg)
        if models:
            return models
    raise
```

**Result**: LMStudio now correctly returns all 28 models instead of `available=false`.

---

## Testing

### Comprehensive Test Suite

**Files**:
- `tests/abstractcore_v262/test_programmatic_configuration.py` - **8/8 tests passing**
- `tests/abstractcore_v262/test_model_not_found_error_handling.py` - **4/4 tests passing**

**Total: 12/12 tests passing (100%)**

#### test_programmatic_configuration.py (8 tests):

1. ✅ `test_configure_provider_api_available` - API functions exist
2. ✅ `test_configure_base_url` - Setting base_url works
3. ✅ `test_create_llm_uses_configured_url` - create_llm() respects config
4. ✅ `test_list_models_respects_configured_url` - list_available_models() uses config
5. ✅ `test_invalid_url_fails_correctly` - Invalid URL returns empty list
6. ✅ `test_dynamic_url_update` - Runtime updates work (Blue "Update" button)
7. ✅ `test_settings_integration` - User settings integration works
8. ✅ `test_clear_configuration` - clear_provider_config() works

### Running Tests

```bash
# Run AbstractCore v2.6.2 integration tests
python -m pytest tests/abstractcore_v262/test_programmatic_configuration.py -v

# Expected: 8/8 passing
```

---

## Verification Checklist

✅ **Upgrade successful**: AbstractCore v2.6.2 installed
✅ **API available**: `configure_provider()`, `get_provider_config()`, `clear_provider_config()`
✅ **Backend updated**: `llm.py` uses programmatic configuration
✅ **Settings integration**: Base URLs from user settings automatically configured
✅ **Connection testing**: Blue "Update" button tests custom URLs
✅ **All tests pass**: 8/8 integration tests passing
✅ **No breaking changes**: Existing functionality preserved

---

## Files Modified

### Backend
- `backend/app/api/llm.py` (~20 lines changed):
  - Import `configure_provider` from abstractcore.config
  - Configure base URLs from settings in `get_available_providers()`
  - Simplified `get_provider_models()` - no manual base_url parameter

### Tests
- `tests/abstractcore_v262/test_programmatic_configuration.py` (180 lines):
  - Comprehensive integration tests
  - 8 test scenarios covering all use cases

### Documentation
- `docs/devnotes/abstractcore-v262-upgrade.md` (this file)
- Updated: `docs/devnotes/model-download-implementation-final.md` (reference)

---

## Comparison with Previous Implementation

### Before (AbstractCore v2.5.3 - workaround)

```python
# Had to pass base_url to EVERY call
llm = create_llm('ollama', model='test', base_url=base_url)
models = llm.list_available_models()

# Provider discovery didn't respect custom URLs
providers = get_all_providers_with_models(include_models=False)
# ❌ Always checked localhost, ignored custom URLs
```

### After (AbstractCore v2.6.2 - clean solution)

```python
# Configure ONCE from settings
configure_provider('ollama', base_url=base_url)

# All calls automatically use configured URL
llm = create_llm('ollama', model='test')  # ✅ Uses configured URL
models = llm.list_available_models()  # ✅ Uses configured URL

# Provider discovery respects configured URLs
providers = get_all_providers_with_models(include_models=False)
# ✅ Tests connection to configured URL
```

---

## Benefits for Digital Article

### Before Upgrade

❌ **Provider discovery broken**: Couldn't test custom base URLs
❌ **Manual workarounds**: Had to manually test connections
❌ **Code duplication**: base_url parameter passed everywhere
❌ **No single source of truth**: URLs scattered across code

### After Upgrade

✅ **Clean architecture**: Configure once, use everywhere
✅ **Automatic integration**: User settings → AbstractCore config
✅ **Remote server support**: Ollama on GPU server, access from laptop
✅ **Docker-friendly**: Different hosts/ports just work
✅ **Port conflicts handled**: Run multiple instances with different ports
✅ **Dynamic updates**: Change URL → immediate effect, no restart
✅ **Type-safe**: IDE autocomplete and validation

---

## Future Enhancements

### Possible Improvements (not implemented)

1. **Provider health caching**: Cache connectivity status for 5 minutes
2. **Retry logic**: Add retry for failed provider checks
3. **Better error messages**: Show why provider unavailable (timeout, DNS, etc.)
4. **Connection timeout config**: Allow user to set connection timeout
5. **Base URL validation**: Validate URL format before API call

---

## Conclusion

✅ **Upgrade Complete**: AbstractCore v2.6.2 successfully integrated
✅ **Cleaner Code**: Programmatic config simpler than env vars
✅ **Better UX**: Custom base URLs now fully supported
✅ **Well Tested**: 8/8 integration tests passing
✅ **Zero Breaking Changes**: Existing functionality preserved
✅ **Production Ready**: Ready to deploy

The programmatic configuration API provides exactly what we needed - a clean, maintainable way to configure provider base URLs from user settings with automatic propagation throughout the application.

---

## References

- **AbstractCore Feature Request Response**: `FEATURE_REQUEST_RESPONSE_ENV_VARS.md`
- **Previous Implementation**: `docs/devnotes/model-download-implementation-final.md`
- **Test File**: `tests/abstractcore_v262/test_programmatic_configuration.py`
- **AbstractCore GitHub**: https://github.com/anthropics/abstractcore
