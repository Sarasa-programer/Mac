# Frontend Debugging Guide (React + Vite + TS)

## Phase 1: Rapid Diagnosis (First 5 Minutes)

1.  **Check Console Errors**: Look for `Uncaught TypeError` (null pointers) or `Network Error`.
2.  **Verify Backend Connection**:
    *   Open `Network` tab.
    *   Reload page.
    *   Check `OPTIONS` and `POST` requests to `/api/v1/...`.
    *   If `404`, check backend router registration (`src/main.py`).
    *   If `500`, check backend logs (`docker logs` or terminal).
3.  **Inspect React Tree**:
    *   Use React DevTools to check `ErrorBoundary` state.
    *   Identify which component is rendering `null` or crashing.

---

## Phase 2: Debugging Decision Tree

### **Case 1: White Screen (No UI)**
*   **Cause**: Uncaught error in main render loop.
*   **Fix**:
    1.  Check `main.tsx` - is `ErrorBoundary` wrapping `App`? (We just added this).
    2.  Check `App.tsx` imports - are any failing?
    3.  Check Console for `Minified React error` - click the link to decode.

### **Case 2: "Network Error" or API Failure**
*   **Cause**: Backend down, CORS, or wrong URL.
*   **Fix**:
    1.  Check `frontend/src/api/client.ts` -> `baseURL`.
    2.  Verify backend is running on `http://localhost:8000`.
    3.  Check CORS in `backend/src/main.py` (Allowed origins must match frontend port).

### **Case 3: Infinite Loading Spinner**
*   **Cause**: `await` never resolving or state update loop.
*   **Fix**:
    1.  Check `Network` tab - is the request pending forever?
    2.  Check `useEffect` dependencies - is it re-triggering constantly?

---

## Phase 6: Solution Templates

### 1. Safe Data Fetching (Use `useSafeAsync`)
Instead of manual `useEffect` fetching:
```typescript
import { useSafeAsync } from '../hooks/useSafeAsync';
import { apiClient } from '../api/client';

const MyComponent = () => {
  const { data, loading, error, execute } = useSafeAsync(
    () => apiClient.get('/some-endpoint').then(r => r.data)
  );

  useEffect(() => {
    execute();
  }, [execute]);

  if (loading) return <Spinner />;
  if (error) return <ErrorDisplay error={error} />;
  return <div>{data?.message}</div>;
};
```

### 2. Error Boundary Usage
Already implemented in `src/main.tsx`. To protect a specific widget:

```tsx
<ErrorBoundary fallback={<WidgetErrorFallback />}>
  <ComplexChartWidget />
</ErrorBoundary>
```

### 3. Null Safety (TypeScript)
Use Optional Chaining (`?.`) and Nullish Coalescing (`??`):

```typescript
// BAD
const name = user.profile.name;

// GOOD
const name = user?.profile?.name ?? 'Anonymous';
```

---

## Quick Reference Checklist

- [ ] **Console**: No red errors?
- [ ] **Network**: API calls return 200/201?
- [ ] **React**: Components verify props are defined?
- [ ] **Hooks**: Dependency arrays in `useEffect` are correct?
- [ ] **Imports**: No circular dependencies?
