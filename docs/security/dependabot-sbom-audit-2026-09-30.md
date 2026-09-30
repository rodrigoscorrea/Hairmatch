# Relatório de dependências e vulnerabilidades — Hairmatch

## Status (PR da issue #166)

Aplicado nesta branch, com testes:

- **Frontend:** `npm audit fix` (sem `--force`) + `brace-expansion` atualizado + `query-string@^9.5.1` como dependência **explícita**. Resultado medido: **53 → 22** alertas (restam os 21 da cadeia Expo SDK 52 e `image-size`, só build/Metro).
  - **Achado durante a validação:** o novo `@react-navigation/core` deixou de depender de `query-string`, mas o `expo-router@4.0.20` o importa sem declarar (dependia do hoist). Sem a dependência explícita, `expo export` falhava com *Unable to resolve "query-string"*. O `expo-router` só chama `stringify(..., {sort:false})`, que não passa pelo `decode-uri-component` vulnerável.
  - Validado: `npx tsc --noEmit` limpo; `npx expo export` para **android** e **web** OK. O app não tem testes automatizados de propósito (`jest` sem testes).
- **Backend:** `Django 4.2.20 → 4.2.30` e Python **3.9 → 3.12** (`docker/backend/Dockerfile`, workflow), o que destrava `Pillow 11.3 → 12.3` (36 CVEs), `urllib3 1.26 → 2.8`, `sqlparse 0.5.5 → 0.6.0`, `requests 2.32 → 2.34`, `djangorestframework 3.15.0 → 3.17.2` e `boto3/botocore`. `requirements.txt` ganhou pisos (`Pillow>=12.3.0,<13`, `requests>=2.33,<3`, `sqlparse>=0.6.0`) para essas correções não regredirem. Nova varredura OSV das versões instaladas na imagem 3.12: **só restam os 7 alertas do Django 4.2** (LTS sem suporte; sem exposição neste app).
  - Validado na imagem 3.12: `manage.py check`, `makemigrations --check` (sem mudanças), suíte completa **598 testes OK** (igual ao baseline em 3.9), conversão WebP de JPEG/JPEG-CMYK/PNG-alpha/PNG-cinza/WebP/GIF/BMP idêntica à do 3.9 (lixo e arquivo truncado seguem dando `InvalidImage`), `runserver` sobe respondendo problem+json, e `default_storage` grava/lê/apaga no S3 do LocalStack com boto3 1.43 + urllib3 2.8.
  - **Ao atualizar o ambiente local:** rebuild da imagem (`docker compose build backend`); o container antigo ainda é Python 3.9.
- **CI:** `actions/checkout@v3 → v4`, `actions/setup-python@v4 → v5` (só o próprio CI valida).

**Não feito (fora de escopo):** fixar todo o `requirements.txt` com lockfile, `dependabot.yml`, Expo SDK 57, Django 5.2 LTS, migração do `google-generativeai` (agora emite aviso de fim de suporte; ver §2.3). As seções abaixo são a análise original, feita antes do bump de Python.

---

> Fonte: SBOM SPDX-2.3 do Dependabot (`rodrigoscorrea_Hairmatch_a92827.json`, branch `develop`, gerado em 2026-09-30).
> O SBOM **só lista pacotes** (1057: 1041 npm, 13 PyPI, 2 GitHub Actions) — não traz CVEs. Os achados abaixo vêm de:
> - **npm**: `npm audit --package-lock-only` sobre `frontend-mobile/package-lock.json` (53 achados: 3 críticos, 24 altos, 21 moderados, 5 baixos).
> - **Python**: consulta ao OSV.dev com as versões **realmente instaladas** no container `hairmatch_backend` (Python 3.9.25) — o SBOM só resolveu versão de 3 dos 13 pacotes PyPI, porque `requirements.txt` não fixa o resto.
> - **Exposição real**: leitura do código (`backend/hairmatch/images.py`, `settings.py`, uso de libs) para separar "vulnerável na árvore" de "alcançável pelo app".

## Resumo executivo

| Área | Achados | Corrigível sem quebrar o app | Bloqueado / aceitar |
|---|---|---|---|
| Frontend (npm) | 53 | **30 eliminados** via `npm audit fix` (sem `--force`), **medido** numa cópia do lockfile: 53 → 23 (0 baixos, 15 moderados, 7 altos, 1 crítico) | **21** exigem Expo SDK 52→57 (cadeia `expo`/`@expo/cli`) + **2** cópias aninhadas (`brace-expansion`, `image-size`) que o 1º passe não resolve — ver §1.1 |
| Backend (Python 3.9) | Django 51, Pillow 36, urllib3 12, sqlparse 10, DRF 6, requests 2 | Django→4.2.30 (−44), DRF→3.15.2 (−1) | Pillow, urllib3, sqlparse, requests, resto do DRF/Django: **exigem Python ≥ 3.10** |
| CI / Docker | — | `actions/checkout@v3`, `setup-python@v4` desatualizados | `python:3.9` e `postgres:13` fora de suporte |

**A causa-raiz do lado Python é uma só: o Python 3.9 (EOL desde out/2025).** Quase tudo que "não dá para corrigir" no backend vira corrigível ao subir para Python 3.12 — que é a decisão de maior valor e maior risco desta lista.

**O achado que mais importa de verdade:** Pillow 11.3.0 (36 CVEs, 18 altos). O app chama `Image.open()` em **uploads de usuário** (`backend/hairmatch/images.py:37`, via `WebPImageField` em foto de perfil, review e preferências). Todos os 36 só são corrigidos no Pillow 12.x, que exige Python ≥ 3.10.

---

## 1. Frontend — `frontend-mobile` (npm)

O `package.json` da raiz é `{}`; todo o npm vem de `frontend-mobile/`. Dos 53 alertas, só uma minoria chega ao **bundle que roda no celular**; a maioria é ferramenta de build/dev (Expo CLI, Metro, Jest).

### 1.1 Corrigir agora — dentro do semver, sem mudar API (`npm audit fix`; medido: 53 → 23)

> Medição feita numa **cópia** de `package.json`/`package-lock.json` (`npm audit fix --package-lock-only`); o repositório não foi tocado. 149 entradas do lockfile mudam. Nenhum pacote pinado pela SDK do Expo saiu da faixa (só `expo` 52.0.46 → 52.0.49, patch da mesma SDK; `react`, `react-native`, `expo-*`, `react-native-*` intactos). `@react-navigation/*` continua com **uma única cópia** deduplicada (`native` 7.1.6→7.5.0, `core` 7.8.5→7.23.0, `routers` 7.3.5→7.6.4), evitando o risco de contexto de navegação duplicado — mas são saltos de vários minors, então testar as telas de navegação.

**Vão para o bundle do app (prioridade):**

| Pacote | Severidade | Origem | Observação |
|---|---|---|---|
| `axios` 1.9.0 | alta (DoS, bypass de NO_PROXY, proto-pollution gadget) | **direta** (`^1.9.0`) | corrige em 1.x; usado em `services/axios-instance.ts` |
| `@react-navigation/native` 7.1.6 (+ `core`, `routers`) | alta | **direta** | via `nanoid`; corrige em 7.x |
| `nanoid` 3.3.8 | alta | transitiva | idem |
| `query-string` 7.1.3 / `decode-uri-component` | moderada | via react-navigation/core | |
| `lodash` 4.17.21, `moment` 2.30.1 | alta / moderada | via `react-native-calendars` | patch/minor |
| `follow-redirects`, `form-data` (dentro do axios) | moderada / **crítica** | axios | em React Native o axios usa o adapter XHR; o caminho vulnerável (Node) não é executado no app — mas sobe junto de graça |
| `uuid` raiz 11.1.0 → 11.1.1 | moderada | **direta** | o `npm audit fix` já sobe a raiz para 11.1.1; o alerta **permanece** por causa das cópias 7.x/8.x aninhadas em `xcode`/`@expo/bunyan` (contadas nos 21 do §1.2). Só é explorável em v3/v5/v6 com `buf` |

**Ferramentas de build/dev (também corrigidas sem risco de runtime):** `shell-quote` (crítico, via react-devtools-core), `@babel/plugin-transform-modules-systemjs`, `@babel/core`, `browserslist`, `minimatch`, `picomatch`, `glob`, `js-yaml`, `fast-uri`, `ajv`, `node-forge`, `undici`, `ws`, `serialize-javascript`, `terser-webpack-plugin`, `webpack`, `compression`, `on-headers`, `@tootallnate/once`, `form-data` (crítico, nas cópias do `@expo/cli`).

**Sobram após o 1º passe, mas ainda têm correção sem major (2, altos):** `brace-expansion` e `image-size` — cópias aninhadas cujas faixas nas ferramentas Metro/Jest impedem o bump. Tentar um 2º `npm audit fix`; se persistirem, `overrides` pontual em `package.json` (`brace-expansion`, `image-size` no mesmo major) e validar `expo export`. São só ferramentas de build.

**Como aplicar sem afetar o app:** `cd frontend-mobile && npm audit fix` — **nunca `--force`** (o `--force` move `expo` para 57 e `jest-expo` para 57, o que quebra o app). Depois validar: `npx expo install --check` (garante que nenhum pacote pinado pelo Expo saiu da faixa da SDK 52), `npx tsc --noEmit`, `npm test -- --watchAll=false`, `npx expo export` (smoke do bundle).

### 1.2 Não corrigível sem migrar o Expo (21 pacotes, 1 crítico + 5 altos + 15 moderados) — aceitar/dispensar

Todos exigem `expo@57.0.26` (isSemVerMajor). Cadeia: `expo@52 → @expo/cli / @expo/config-plugins / @expo/metro-config`.

| Pacote (versão no lock) | Sev. | Por que é baixo risco |
|---|---|---|
| `tar` 6.2.1 (via `cacache`, `@expo/cli`) | **crítica** | roda só na máquina do dev/EAS ao instalar/baixar templates; nunca no app. Só exploraria se o dev extrair tarball malicioso |
| `@xmldom/xmldom` 0.7.13 / 0.8.10 (via `@expo/plist`, `plist`) | alta | parse de plist/manifest do **próprio projeto** no prebuild |
| `postcss` 8.4.49 (via `@expo/metro-config`) | alta | build de web/Metro, entrada é o CSS do próprio projeto |
| `uuid` 7.0.3 / 8.3.2 (via `xcode`, `@expo/bunyan`) | moderada | só exploráveis com o argumento `buf` em v3/v5/v6; `xcode` usa v4 |
| `@expo/cli`, `cacache`, `expo`, `@expo/config*`, `@expo/prebuild-config`, `@expo/rudder-sdk-node`, `@expo/bunyan`, `@expo/plist`, `xcode`, `expo-asset`, `expo-constants`, `expo-linking`, `expo-auth-session`, `expo-splash-screen`, `jest-expo` | alta/moderada | **alertas "por propagação"**: só herdam severidade dos de cima (`tar`/`xmldom`/`uuid`); não têm CVE própria |

Observação: os "direct" `expo-constants`, `expo-linking`, `expo-auth-session`, `expo-splash-screen`, `jest-expo` aparecem como vulneráveis **só** porque dependem de `@expo/config` → build-time.

**Recomendação:** dispensar no Dependabot como *"vulnerable code is not actually used / tolerable risk"* e tratar como um item de roadmap separado: **upgrade de Expo SDK 52→57** (RN 0.76→0.8x, React 18→19, expo-router 4→6…). Não é uma correção "sem afetar o app". Alternativa de meio-termo, se quiser reduzir ruído: `overrides` em `package.json` só para `postcss` (>8.5.22, mesmo major) e `@xmldom/xmldom` (0.8.x recente). **Não** fazer override de `tar` (6→7 é major e o `@expo/cli` usa a API antiga).

---

## 2. Backend — Python (`backend/requirements.txt`, container Python 3.9.25)

### 2.1 Corrigir agora — compatível com Python 3.9, sem quebrar o app

| Pacote | Atual → alvo | Efeito | Risco |
|---|---|---|---|
| `Django` | 4.2.20 → **4.2.30** | de 51 para 7 alertas; inclui SQLi crítica (CVE-2025-64459, corrigida em 4.2.26), SQLi em aliases (4.2.24/25), DoS (4.2.29/30) | baixo — só patch dentro do LTS 4.2 |
| `djangorestframework` | 3.15.0 → **3.15.2** | XSS CVE-2024-21520 | baixo — só patch |

Fixar as versões em `requirements.txt` (`Django==4.2.30`, `djangorestframework==3.15.2`) e rodar a suíte no container (`docker exec hairmatch_backend …`, conforme o fluxo de testes do projeto).

### 2.2 Só corrigível subindo o Python para ≥ 3.10 (recomendo 3.12)

| Pacote | Atual | Vulns | Correção | Por que o 3.9 bloqueia |
|---|---|---|---|---|
| **Pillow** | 11.3.0 | **36** (18 altas) | 12.3.0 | 12.x exige Python ≥ 3.10 |
| `urllib3` | 1.26.20 | 12 (6 altas: bombas de descompressão, headers vazados em proxy) | 2.8.0 | `botocore` fixa `urllib3<1.27` quando Python < 3.10 |
| `sqlparse` | 0.5.5 | 10 (3 altas, DoS) | 0.6.0 | 0.6.0 exige ≥ 3.10 |
| `djangorestframework` | 3.15.2 | 2 moderadas restantes | 3.17.2 | exige ≥ 3.10 |
| `requests` | 2.32.5 | 1 moderada (CVE-2026-25645, `extract_zipped_paths`) | 2.33.0 | exige ≥ 3.10 |

**Exposição real de cada um (por que o Pillow é o item crítico e o resto pode esperar):**
- **Pillow — exposição ALTA.** Uploads de usuário passam por `Image.open(content)` sem restringir formatos. Muitos dos CVEs são de formatos/rotinas que o app nem precisa (PSD, FITS, PDF, GD, fontes BDF/PCF, JPEG2000, `ImageFilter`, `WindowsViewer`) — o que dá uma **mitigação opcional no 3.9**: `Image.open(content, formats=[…])` limitando aos formatos aceitos (JPEG/PNG/WebP/…), mudança de 1 linha em `images.py:37`. Só aplicar depois de confirmar quais formatos o app precisa aceitar (ex.: HEIC do iOS, GIF) — restringir demais muda comportamento.
- **urllib3 / requests — exposição baixa.** Só falam com endpoints S3/LocalStack, APIs do Google e o provedor de CEP (`users/cep_lookup.py`); as falhas exigem resposta maliciosa/redirect/proxy. `requests` só usa `get`/`post`, nunca `extract_zipped_paths`.
- **sqlparse — exposição baixa.** O Django só o usa em `RunSQL`/`sqlmigrate` (SQL escrito pelo dev, não por usuário).
- **DRF restantes — baixa.** `REST_FRAMEWORK` só define `EXCEPTION_HANDLER`; `AdminRenderer` não é usado. O bypass de `DATA_UPLOAD_MAX_MEMORY_SIZE` é o único que merece atenção e some com o Python ≥ 3.10.

**Risco do bump para Python 3.12:** médio-baixo. Django 4.2.30 suporta 3.12; o código de imagem usa só APIs que continuam no Pillow 12 (`Image.Resampling.LANCZOS`, `draft`, `ImageOps.exif_transpose`, `Image.DecompressionBombError`). Precisa de: `docker/backend/Dockerfile` (`FROM python:3.12`), `.github/workflows/hairmatch-backend-test.yml` (`python-version`), rebuild da imagem, suíte completa passando (incluindo os testes de imagem/WebP e os de upload S3) (DRF 3.17.2 declara suporte a Django 4.2, 5.x e 6.0 e a Python 3.10–3.14 — verificado no PyPI; então dá para ficar em Django 4.2.30 no 3.12 sem migrar o Django).

### 2.3 Não corrigível (aceitar/dispensar)

- **Django 4.2.30 — 7 alertas restantes (5 baixos, 2 moderados)**: o LTS 4.2 saiu de suporte em abril/2026, então não recebe mais patches; só o 5.2 LTS (exige Python ≥ 3.10) corrige. Exposição efetiva ≈ nula neste app: sem `UpdateCacheMiddleware`/cache (não está em `MIDDLEWARE`), sem `contrib.gis` (GDALRaster), sem cookies assinados como sessão, sem `DomainNameValidator`. O `PYSEC-2026-3717` (CVE-2026-15830) é DoS em `GEOSGeometry` do GeoDjango — o app não usa `contrib.gis`; corrigido só em 5.2.17+/6.0.8. Caminho definitivo: **Django 5.2 LTS** (migração própria, item de roadmap).
- **`google-generativeai` 0.8.6**: sem CVE, mas o SDK está descontinuado em favor de `google-genai` (verificar o aviso de fim de suporte). Item de manutenção, não de segurança — migrar mexe em `chatbot/ai_utils.py` e `hairmatch/ai_clients/gemini_client.py`.

---

## 3. Lacunas que geram ruído / ponto cego no Dependabot

1. **`requirements.txt` sem versões fixas** (Pillow, requests, boto3, PyJWT, google-auth, Faker, coverage, django-filter, psycopg2, google-generativeai): o SBOM diz `versionInfo: None` para 10 dos 13 → o Dependabot **não consegue alertar** sobre eles (o Pillow, o mais grave, provavelmente nem aparece nos seus alertas). Fixar com lockfile (`pip-compile`/`uv pip compile`) resolve isso.
2. **Sem `.github/dependabot.yml`**: não há agrupamento nem regra para ignorar major do Expo. Sugestão: ecossistemas `npm` (`/frontend-mobile`, ignorar `expo*`/`react-native*` major), `pip` (`/backend`), `github-actions` e `docker`.
3. **GitHub Actions**: `actions/checkout@v3` e `actions/setup-python@v4` → subir para v4+/v5+ (sem impacto no teste; runtime Node antigo). Não verifiquei CVE específico desses.
4. **Fora do escopo do SBOM, mas relevante:** `settings.py:28` tem `DEBUG = True` fixo; `postgres:13` (EOL nov/2025) no `docker-compose.yml` e no workflow.

---

## Plano de execução recomendado (ordem, menor → maior risco)

1. **Frontend:** `npm audit fix` em `frontend-mobile/` + validações (§1.1). Mede-se 53 → 23; depois tratar `brace-expansion`/`image-size` (→ 21).
2. **Backend seguro no 3.9:** `Django==4.2.30`, `djangorestframework==3.15.2`, rodar testes no container.
3. **Higiene:** fixar todas as versões Python; adicionar `dependabot.yml`; atualizar Actions.
4. **Decisão sua — Python 3.9 → 3.12** (Dockerfile + workflow + Pillow 12.3 / sqlparse 0.6 / requests 2.33 / urllib3 2.x / DRF 3.17): elimina ~60 dos alertas Python restantes, incluindo os 36 do Pillow.
5. **Dispensar no Dependabot** (com justificativa "build-time only / não alcançável"): os 21 do Expo e os 7 residuais do Django 4.2.
6. **Roadmap:** Expo SDK 57, Django 5.2 LTS, migração `google-generativeai` → `google-genai`.

## Verificação (quando for aplicar)

- Frontend: `npm audit --package-lock-only` deve cair de 53 para 23 (21 da cadeia `expo`/`@expo/*` + `brace-expansion` e `image-size`, resolvíveis no 2º passe/override); `npx expo install --check`, `npx tsc --noEmit`, `npm test -- --watchAll=false`, `npx expo export`.
- Backend: `docker exec hairmatch_backend python manage.py test` (subir `hairmatch_db` antes se parado); reconsultar OSV com `pip freeze` após as trocas.
- Após Python 3.12: rebuild da imagem, suíte completa e upload manual de uma foto (JPEG/PNG/HEIC) para confirmar a conversão WebP.
