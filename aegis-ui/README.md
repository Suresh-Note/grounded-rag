# GroundedRAG — Frontend

The dashboard for [GroundedRAG](../Agentic-RAG-for-Enterprise-Compliance/README.md): upload a contract, watch the multi-agent audit pipeline run live over SSE, and inspect each finding against the exact quoted evidence it was verified against.

Built with React, Vite, TypeScript, and Tailwind.

## Development

```bash
npm install
npm run dev
```

The dev server expects the API at `http://localhost:8000` (see `VITE_API_URL` in `vite.config.ts` / the Docker build args). Run the backend and its services first — see the [root README](../README.md) for the full stack.

## Build

```bash
npm run build   # outputs to dist/, served via nginx in the Docker image
```
