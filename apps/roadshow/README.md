# 13110 Roadshow

Independent, static, cinematic opening frontend for 13110. It does not call the product API or import the existing Presentation Hall runtime.

## Commands

```bash
npm ci
npm run dev
npm test
npm run build
npm run test:sites
npm run check:isolated
```

`npm run build` emits the deployable client under `dist/client` and the optional Sites worker under `dist/server`.

## Boundaries

- All runtime data and media are local to this directory.
- No CDN, remote texture, `/api` request, or cross-app import is allowed.
- `references/` contains QA sources and is not shipped in the production bundle.
