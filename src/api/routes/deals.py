"""Deal Endpoints.

POST /api/v1/deals          - Submit a deal with document manifest
GET  /api/v1/deals/{id}/status  - Stream progress via WebSocket/SSE
GET  /api/v1/deals/{id}/verdict - Compiled structured JSON verdict
GET  /api/v1/deals/{id}/audit   - Immutable debate transcripts
"""
