---
title: Dev Dito Secrets Directory
description: Documentation for required secret files (API tokens, SSL certificates, API keys) following Constitution Article VI secret containment.
author:
  name: Jan Ritt
  github: 'https://github.com/IxI-Enki'
version: 1.0.0
created: 2025-12-01
updated: 2026-02-13
tags: [secrets, configuration, security, tokens, article-vi]
---

# Dev Dito Secrets Directory

> **WARNING**: Files in this directory contain sensitive data!
> They are excluded by `.gitignore` and MUST NEVER be committed.

## Benoetigte Secrets

| Datei | Beschreibung | Quelle |
|-------|--------------|--------|
| `json_rpc_api.token` | DokuWiki JSON-RPC API Bearer Token | Wiki Admin → Plugins → JSON-RPC → Token generieren |
| `ssl.cert` | SSL Zertifikat fuer HTTPS Verbindung zum Wiki | `openssl s_client -connect wiki.example.com:443` |
| `openai.token` | OpenAI API Key fuer Embeddings | [OpenAI Platform](https://platform.openai.com/api-keys) |

## Datei-Format

### json_rpc_api.token
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```
(Nur der Token, keine `KEY=` Prefix)

### ssl.cert
```
-----BEGIN CERTIFICATE-----
MIIDdzCCAl+gAwIBAgIEAgAAuTANBgkqhkiG9w0BAQUFADBaMQswCQYDVQQGEwJJ
...
-----END CERTIFICATE-----
```

### openai.token
```
sk-proj-...
```

## Migration von vorhandenen Secrets

Falls Secrets bereits in `pipeline/01_wiki_fetcher/config/` existieren:

```powershell
# Von PowerShell im Repository-Root:
Copy-Item "pipeline/01_wiki_fetcher/config/json_rpc_api.token" "config/secrets/"
Copy-Item "pipeline/01_wiki_fetcher/config/ssl.cert" "config/secrets/"
```

## Sicherheitshinweise

1. **Niemals** Secrets in Code oder Logs ausgeben
2. **Niemals** Secrets in Git committen (`.gitignore` prueft das)
3. **Regelmässig** Token rotieren
4. **Backup** an sicherem Ort aufbewahren (nicht in Cloud-Sync)

---

*Constitution Article VI: Secret Containment*
