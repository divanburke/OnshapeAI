# Architecture

## Runtime

- React + Vite serves the local browser interface on 127.0.0.1:5173.
- FastAPI serves the local application API on 127.0.0.1:8000.
- The browser never calls Onshape directly. The backend signs requests using the API key and secret from environment configuration.
- AI requests go to either the configured Ollama-compatible endpoint or the configured cloud OpenAI-compatible endpoint.

## Main backend modules

- app/settings.py: environment-backed settings and secret wrappers.
- app/security/onshape_signing.py: Onshape HMAC-SHA256 request headers.
- app/onshape/client.py: versioned Onshape REST client, GET caching, concurrency gate, error mapping.
- app/usage/guard.py: app-instance counters and TTL cache.
- app/ai/provider.py: local/cloud chat completion adapter.
- app/agent/planner.py: prompt policy and reviewable CAD plan generation.
- app/api/routes.py: browser-facing API endpoints.

## CAD workflow

1. Read document metadata and tabs.
2. Select the target document, workspace and Part Studio.
3. Ask the model for a proposed operation sequence.
4. Review dimensions, assumptions and the required feature-definition schema.
5. Only send a write request after the user explicitly confirms the exact payload.

The generic feature write route is intentionally low-level. The application does not guess undocumented feature parameter schemas. Confirm schemas against the Glassworks API Explorer and test on a disposable document before relying on a generated operation.

FeatureScript output is draft source. Publishing or running FeatureScript requires a separately designed, explicit workflow and must not happen automatically from an AI response.

## API usage

The app caches selected GET requests for a short configurable interval and caps concurrent calls. A cache hit does not call Onshape. The in-memory counter only records responses observed by this process and resets when the backend restarts. It does not include requests made in the Onshape browser, other apps, or other processes. Onshape Developer settings are authoritative for annual allocation.

## Before internet deployment

This project is currently a local-development application. Before exposing it to a network, add authenticated users, CSRF protection for state-changing browser requests, HTTPS, secure secret storage, audit logging, and deployment-specific CORS/host restrictions.
