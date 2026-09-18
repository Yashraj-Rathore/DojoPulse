# System context

```mermaid
flowchart LR
  P[Player] --> UI[Thin Next.js client]
  UI --> API[Django / DRF]
  API --> DB[(PostgreSQL)]
  P --> C[Local capture CLI]
  C --> E[Private evidence artifacts]
  C --> R[Structured report / review required]
  H[Authorized reviewers] --> R
  R --> API
  K[Versioned knowledge and contracts] --> C
  DB --> V[Evaluation application service]
  V --> UI
```

The CLI executes media work outside requests. The initial API manages local pilot metadata
and results, not arbitrary public media uploads. No running game process, third-party mod,
LLM or remote website is consulted during analysis. Owner and participant are separate identities.
