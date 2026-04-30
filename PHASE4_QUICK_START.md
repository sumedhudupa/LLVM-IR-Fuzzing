# Phase 4 Quick Start Guide

**Status**: Ready to begin  
**Duration**: 2-3 days estimated  
**Complexity**: Medium

---

## Phase 4 Overview

Phase 4 focuses on **Testing and Documentation**. The core functionality (Phase 1-3) is complete and tested. Phase 4 ensures production readiness through:

1. Integration testing
2. Documentation updates
3. Frontend enhancements
4. Performance validation

---

## Quick Facts

### What's Already Done (Phase 1-3)
✅ RandomMutator (5 strategies)  
✅ RuleValidator (7 checks)  
✅ IRDeduplicator (hashing)  
✅ LLM Refinement Loop  
✅ Subprocess Isolation  
✅ ManifestTracker Service  
✅ Manifest API Endpoint  
✅ 16 Unit Tests (100% passing)  

### What Needs Phase 4
⏳ Integration tests (end-to-end)  
⏳ Backward compatibility tests  
⏳ Frontend updates  
⏳ Documentation updates  

---

## Phase 4 Tasks

### High Priority (1-2 days)

**1. Integration Tests**
- **File**: `llm-mutator/tests/test_integration_phase3.py`
- **What to test**:
  - End-to-end pipeline (all mutator types)
  - Manifest generation with mixed mutators
  - Validation completeness
  - Statistics accuracy
- **Resources**: See existing `tests/verify_mutators.py` for pattern
- **Estimated Time**: 1 day

**2. Backward Compatibility**
- **Run**: `pytest tests/` to verify all existing tests still pass
- **Check**: No changes to existing API contracts
- **Expected**: All existing tests should pass unchanged
- **Estimated Time**: 2 hours

**3. Frontend Updates**
- **File**: `frontend/src/pages/ComparisonView.jsx`
- **Updates needed**:
  - Add manifest query on mount
  - Display trivial (valid) column
  - Add per-strategy breakdown table
  - Add seed sensitivity table
  - Add study run history panel
- **Reference**: `frontend/src/api.js` for API patterns
- **Estimated Time**: 1.5 days

### Medium Priority (0.5 days)

**4. Documentation Updates**
- **File**: `README.md` (add Phase 3 section)
- **Updates needed**:
  - Document new features
  - Add manifest endpoint to API docs
  - Update configuration section
  - Add usage examples
- **Template**: See `PHASE3_MANIFEST_DOCUMENTATION.md`
- **Estimated Time**: 4 hours

### Optional (Nice to have)

**5. Performance Testing**
- Run with 1000+ mutants
- Measure manifest generation time
- Verify no memory leaks
- Document performance characteristics

**6. Additional Tests**
- RandomMutator unit tests
- RuleValidator unit tests
- IRDeduplicator unit tests
- Integration with refinement loop

---

## Getting Started

### 1. Run Current Tests
```bash
cd llm-mutator
python -m pytest tests/test_phase3.py -v
# Expected: 16/16 passing
```

### 2. Check Existing Tests
```bash
python -m pytest tests/ -v
# Verify all existing tests still pass
```

### 3. Generate Test Data
```bash
cd llm-mutator
python -m pytest tests/test_phase3.py::TestManifestTracker::test_generate_manifest_aggregates_data -v
# Validates real-world scenario
```

### 4. Review Manifest Output
```bash
cat logs/manifest.json | python -m json.tool
# Verify schema and data
```

### 5. Test API Endpoint
```bash
# Start backend (if running)
curl http://localhost:8000/api/v1/manifest | python -m json.tool
```

---

## Key Files for Phase 4

### Backend
```
llm-mutator/app/services/manifest_service.py       ← Core service (no changes needed)
llm-mutator/app/routes/analysis.py                 ← Endpoint (ready to use)
llm-mutator/app/services/analysis_service.py       ← Service integration (ready)
llm-mutator/tests/test_phase3.py                   ← Reference for test patterns
```

### Frontend
```
frontend/src/api.js                                ← Add getManifest() function
frontend/src/pages/ComparisonView.jsx              ← Update to use manifest
frontend/src/pages/ValidationStatus.jsx            ← Optional auto-load
```

### Documentation
```
README.md                                          ← Add Phase 3 section
PHASE3_MANIFEST_DOCUMENTATION.md                   ← Reference for detailed docs
INTEGRATION_STATUS_REPORT.md                       ← Overall status
```

---

## Code Patterns to Follow

### Adding Frontend API Call
```javascript
// In frontend/src/api.js
export const getManifest = () => request("GET", "/api/v1/manifest");

// In component
const manifest = await getManifest();
console.log(manifest.summary.total_generated);
```

### Adding Table Column
```jsx
// In ComparisonView.jsx
const COLUMNS = [
  ...existing_columns,
  {
    key: "trivial_valid",
    label: "trivial (valid)",
    render: (value) => value ? "Yes" : "-"
  }
];
```

### Running Tests
```bash
# Single test file
pytest tests/test_phase3.py -v

# Single test case
pytest tests/test_phase3.py::TestManifestTracker::test_summary_statistics -v

# With coverage
pytest tests/test_phase3.py --cov=app.services.manifest_service -v
```

---

## Integration Checklist

- [ ] All Phase 1-3 tests passing
- [ ] Backward compatibility verified
- [ ] Frontend ComparisonView updated
- [ ] Manifest endpoint tested
- [ ] Documentation updated
- [ ] README includes Phase 3 features
- [ ] API documentation current
- [ ] Performance validated
- [ ] Error cases documented
- [ ] User guide created

---

## Common Issues & Solutions

### Issue: Manifest is empty
**Solution**: Ensure raw_mutants.json and validity_logs.json are populated  
```bash
wc -l logs/raw_mutants.json logs/validity_logs.json
```

### Issue: API endpoint returns 500
**Solution**: Check backend logs, ensure LOGS_DIR and SEED_DIR configured correctly  
```python
from app.config import LOGS_DIR, SEED_DIR
print(f"LOGS_DIR: {LOGS_DIR}")
print(f"SEED_DIR: {SEED_DIR}")
```

### Issue: Tests fail
**Solution**: Verify pytest is installed and tests are discovered  
```bash
pip install pytest
python -m pytest tests/test_phase3.py --collect-only
```

### Issue: Frontend can't call API
**Solution**: Check VITE_API_BASE_URL environment variable  
```javascript
console.log(import.meta.env.VITE_API_BASE_URL)
```

---

## Performance Tips

1. **For large datasets** (1000+ mutants):
   - Consider caching manifest.json
   - Add pagination to API response
   - Use lazy loading in frontend

2. **For slow validation**:
   - Verify VALIDATION_TIMEOUT is not too high
   - Check ENABLE_RULE_VALIDATION is not causing delays
   - Consider parallel validation

3. **For frontend performance**:
   - Lazy load manifest data
   - Paginate manifest entries
   - Cache API responses client-side

---

## Success Criteria

### Testing
- [ ] 100% of existing tests passing
- [ ] Integration tests added (5+ scenarios)
- [ ] No regressions in Phase 1-2 features

### Frontend
- [ ] ComparisonView displays manifest data
- [ ] All manifest fields queryable
- [ ] Statistics dashboard updated
- [ ] UX is intuitive

### Documentation
- [ ] README has Phase 3 section
- [ ] API docs include manifest endpoint
- [ ] Examples provided
- [ ] Troubleshooting guide included

---

## Resources

**Phase 3 Documentation**:
- PHASE3_FINAL_SUMMARY.md - Executive overview
- PHASE3_MANIFEST_DOCUMENTATION.md - Detailed API docs
- PHASE3_COMPLETION.md - Implementation details

**Code References**:
- llm-mutator/tests/test_phase3.py - Test patterns
- llm-mutator/app/services/manifest_service.py - Service implementation
- frontend/src/api.js - API call patterns

**Requirements**:
- .kiro/specs/sumadhvabranch-integration/requirements.md - Full specification
- .kiro/specs/sumadhvabranch-integration/IMPLEMENTATION_STATUS.md - Status tracking

---

## Next Steps

1. **Run tests** to verify everything works
2. **Review Phase 3** documentation
3. **Plan Phase 4** tasks
4. **Start integration tests**
5. **Update frontend**
6. **Update documentation**

**Estimated Total Time**: 2-3 days for full Phase 4 completion

---

**Phase 4 Status**: Ready to begin ✅  
**Difficulty**: Medium  
**Success Probability**: High (clear requirements, proven architecture)  

Go forth and complete the integration! 🚀
