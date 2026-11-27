# PayPause Backend Integration Guide (for Ayush & Team)

**Author:** Bhuvan
**Branch:** `feature/bhuvan-backend`
**Target:** Shared `main` / `feature/ayush-core-backend`

---

## 1. Architecture Overview

Bhuvan's modules were built following clean hexagonal architecture principles. Business logic resides in `backend/app/services/` and communicates with persistence and external engines strictly through abstract repository and service interfaces.

```
+-------------------------------------------------------------------+
|                         FastAPI Routers                           |
|  /api/experiments  |  /api/payments  |  /api/subscriptions  | ... |
+---------------------------------+---------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|                        Service Layer                              |
|   ExperimentService, PaymentService, SubscriptionService, etc.    |
+---------------------------------+---------------------------------+
                                  |
                                  v
+-------------------------------------------------------------------+
|               Abstract Dependency Interfaces (ABC)                |
|  - PaymentRepositoryInterface      - IncidentRepositoryInterface  |
|  - SubscriptionRepositoryInterface - ExperimentRepositoryInterface|
|  - DuplicateCheckerInterface       - ScenarioValidatorInterface   |
+---------------------------------+---------------------------------+
          |                                       |
   (Development Adapters)               (Production Adapters — TBD)
          v                                       v
+----------------------------+       +------------------------------+
| InMemory Adapters          |       | Supabase / SQL Adapters      |
| MockScenarioValidator      |       | (to be implemented by team   |
| MockDuplicateChecker       |       |  during integration phase)   |
| (included, tested, active) |       | Not yet implemented.         |
+----------------------------+       +------------------------------+
```

> **Note:** The right-hand column (Supabase / SQL adapters) represents the integration target — these adapters **do not yet exist** in the codebase. The in-memory development adapters on the left are the currently active implementations.

---

## 2. Step-by-Step Integration Procedure

### Step 1: Copy Module Folders
Bring the following directories into the shared repository:
- `backend/app/api/experiments.py`
- `backend/app/api/payments.py`
- `backend/app/api/subscriptions.py`
- `backend/app/api/recovery.py`
- `backend/app/schemas/` (all files)
- `backend/app/services/` (all subdirectories)
- `backend/app/repositories/interfaces/` (all ABCs)
- `backend/app/repositories/development/` (development fallbacks)
- `backend/app/integrations/flagsmith/`
- `backend/tests/bhuvan/`

### Step 2: Register Routers in `main.py`
In Ayush's central `backend/app/main.py`:
```python
from backend.app.api.experiments import router as experiments_router
from backend.app.api.payments import router as payments_router
from backend.app.api.subscriptions import router as subscriptions_router
from backend.app.api.recovery import router as recovery_router

app.include_router(experiments_router)
app.include_router(payments_router)
app.include_router(subscriptions_router)
app.include_router(recovery_router)
```

### Step 3: Replace Authentication Dependency
In `backend/app/core/dependencies.py`:
Replace the development `get_current_user` (which reads an `X-User-Id` header as a convenience for local testing) with Ayush's shared Supabase JWT dependency:
```python
# Before (Development adapter — currently active):
def get_current_user(x_user_id: Annotated[Optional[str], Header(...)]) -> AuthenticatedUser: ...

# After (Production — to be implemented during integration):
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> AuthenticatedUser:
    user = await supabase_auth.verify_token(token)
    return AuthenticatedUser(user_id=user.id, email=user.email)
```

> **Important:** The production Supabase auth integration does not yet exist in the codebase. Do not replace the development adapter until Ayush's shared auth module is available.

### Step 4: Plug In Production Database Repositories
The current active implementations are the in-memory development adapters under `backend/app/repositories/development/`. These must be replaced with production database implementations that fulfil the same abstract interfaces.

Create Supabase (or equivalent) implementations of:
1. `PaymentRepositoryInterface`
2. `IncidentRepositoryInterface`
3. `SubscriptionRepositoryInterface`
4. `ExperimentRepositoryInterface`

Then update the dependency providers in `dependencies.py`:
```python
def get_payment_repo() -> PaymentRepositoryInterface:
    return SupabasePaymentRepository(db_client)
```

> **Important:** These Supabase implementations do not yet exist. The in-memory adapters are development-only; data does not survive application restarts.

### Step 5: Plug In Scenario Validator (Experiment Module)
The experiment module also uses a `ScenarioValidatorInterface` dependency, currently fulfilled by `MockScenarioValidator`. When connecting to a production data source for scenarios (if applicable), implement the same interface and update `get_scenario_validator()` in `dependencies.py`:

```python
def get_scenario_validator() -> ScenarioValidatorInterface:
    return ProductionScenarioValidator(...)
```

> **Security rule:** Canonical expected answers and evaluation criteria must remain strictly backend-only regardless of the validator implementation. They must never be returned by any public API endpoint.

### Step 6: Connect Ayush's Duplicate Detection Engine
Implement `DuplicateCheckerInterface` using Ayush's ML/rule-based engine:
```python
class ProductionDuplicateChecker(DuplicateCheckerInterface):
    def check_payment(self, user_id, amount, transaction_ref, merchant, payment_date):
        # Call Ayush's detection engine
        return DuplicateCheckResult(is_duplicate=..., confidence=..., reason=...)
```
And bind in `dependencies.py`:
```python
def get_duplicate_checker() -> DuplicateCheckerInterface:
    return ProductionDuplicateChecker()
```

### Step 7: Environment Variables
Add to your local `.env` file. **Never commit or share this file** — `.env` is excluded by `.gitignore`. The tracked `.env.example` contains only placeholders:
```ini
FLAGSMITH_ENVIRONMENT_KEY=<flagsmith-server-side-sdk-key>
FLAGSMITH_API_URL=https://edge.api.flagsmith.com/api/v1/
```
