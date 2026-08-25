# AnemiaIA Backend

FastAPI service that receives an eye image and patient metadata, extracts the segmented palpebral conjunctiva, stores the PNG in a private Supabase Storage bucket through its S3-compatible API, and persists a stable image reference in PostgreSQL.

## Project structure

The code follows the same recognizable feature-oriented layout as the Group Loans service while preserving hexagonal boundaries:

```text
main.py                                  # Minimal application bootstrap
src/anemiaiaback/
├── api/
│   ├── api.py                           # App factory, composition and error handlers
│   └── routes.py                        # HTTP route registration
├── capture/
│   ├── application/
│   │   ├── dto/capture_dto.py
│   │   ├── handler/capture_handler.py
│   │   ├── usecase/create_capture_use_case.py
│   │   └── validators.py
│   ├── domain/
│   │   ├── entity/capture.py
│   │   ├── ibucket/iimage_bucket.py
│   │   ├── iprocessor/iconjunctiva_processor.py
│   │   ├── irepository/icapture_repository.py
│   │   └── errors.py
│   └── infrastructure/
│       ├── processing/opencv_conjunctiva_processor.py
│       ├── resources/haarcascade_eye.xml
│       └── storage/
│           ├── local_image_bucket.py
│           ├── postgres_capture_repository.py
│           └── supabase_s3_image_bucket.py
└── internal/
    ├── middleware/body_limit.py
    └── utils/settings.py
```

Dependencies point inward: infrastructure implements domain ports, the use case coordinates processing/storage/persistence, the handler translates multipart HTTP input, and `api.py` composes the concrete adapters.
`LocalImageBucket` remains only as a test/local adapter; production composition always uses `SupabaseS3ImageBucket`.

## Local setup

Requirements: Python 3.10+, `uv`, and PostgreSQL.

```bash
cp .env.example .env
uv sync --extra dev
uv run uvicorn anemiaiaback.api.api:app --reload
```

Configuration is loaded from `.env`. `API_KEY` must contain at least 32 characters. Every `/api/v1` request must send it in `X-API-Key`; `/health`, `/docs`, `/redoc`, and `/openapi.json` intentionally remain public for monitoring and API discovery. Do not embed this shared key in a distributable Android build for production: it is only a controlled test-stage boundary. A production mobile flow requires per-device or per-user authentication.

PostgreSQL uses `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, and `DB_SSLMODE`. TLS is mandatory: `DB_SSLMODE` accepts only `require`, `verify-ca`, or `verify-full`. The connection URL is built safely with SQLAlchemy's `URL.create`, so passwords containing reserved URL characters are supported. `DATABASE_URL` remains an optional compatibility override; a missing `sslmode` is added from `DB_SSLMODE`, while insecure modes are rejected.

Supabase Storage uses `S3_ENDPOINT`, `S3_REGION`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, and `S3_SECRET_ACCESS_KEY`. S3 access keys are server-side credentials: never embed them in the Android application or commit them. The adapter uses the path-style addressing required by the Supabase S3-compatible endpoint. Keep the bucket private because the backend is the only writer. The real values belong only in the ignored `.env`; `.env.example` contains placeholders.

`MAX_REQUEST_BYTES` defaults to the upload limit plus 1 MiB of multipart overhead and cannot be smaller than `MAX_UPLOAD_BYTES`. Invalid configuration fails service startup. Operational storage or database outages keep the API running in degraded state so `/health` can report the outage.

The service uses the existing `patients` table exactly as created by the project: `id`, `image`, `dni`, `age`, and `gender`. It does not create or migrate database tables at startup. Note that PostgreSQL folds an unquoted database name such as `AnemiaIA` to lowercase (`anemiaia`); only a database created as quoted `"AnemiaIA"` retains that exact case. Set `DB_NAME` to the real catalog name shown by PostgreSQL.

## API

Routes are registered in `src/anemiaiaback/api/routes.py`. `POST /api/v1/captures` expects multipart fields: `image` (decodable JPG/PNG), `dni` (exactly 8 digits), `sex` (`M` or `F`), and `age` (integer, at least 0).

```bash
curl -X POST http://127.0.0.1:8000/api/v1/captures \
  -H 'X-API-Key: replace-with-your-api-key' \
  -F 'image=@/absolute/path/eye.jpg' \
  -F 'dni=12345678' \
  -F 'sex=F' \
  -F 'age=34'
```

The response is HTTP 201:

```json
{
  "id": 42,
  "image": "s3://your-private-bucket/550e8400-e29b-41d4-a716-446655440000.png",
  "dni": "12345678",
  "age": 34,
  "gender": "F"
}
```

The `image` value is a stable storage reference, not a public HTTP URL. Upload and compensation delete use the bucket and object key represented by that URI. If PostgreSQL persistence fails after upload, the service deletes the uploaded object on a best-effort basis. Every error uses `{"code": "...", "detail": "..."}`. The global transport guard returns `request_too_large` when the complete body exceeds `MAX_REQUEST_BYTES`; the capture handler returns `image_too_large` when the image field or decoded pixel count exceeds its own limit. Invalid images return 400, size-limit failures 413, form/processing failures 422, storage/configuration failures 500, and unavailable persistence 503.

The original research script processed every Haar detection in a batch. This API creates one capture per request. When Haar returns multiple eyes, it chooses the eye closest to the image center; ties prefer the largest detection, then the topmost, then the leftmost. Processing retains the exact `SEG_HIBRIDO_*` segmentation equations.

## Tests

```bash
uv run pytest
```

The PostgreSQL round-trip test is opt-in and cleans up its record:

```bash
TEST_DATABASE_URL='postgresql+psycopg://postgres:postgres@localhost:5432/anemiaia_test?sslmode=require' \
  uv run pytest -m integration
```

## Deploy to Google Cloud Run

Cloud Build installs Python dependencies remotely, executes the complete test suite in the Docker `test` stage, and only then builds, pushes, and deploys the non-root runtime image. A failed test stops the pipeline before deployment. The image listens on `0.0.0.0:$PORT` as required by Cloud Run.

### 1. Prepare Google Cloud

In Google Cloud Console, select or create a project, attach a billing account, and open Cloud Shell. The free tier still requires billing to be enabled. Set the real values below:

```bash
export PROJECT_ID='your-google-cloud-project-id'
export REGION='us-west1'
export REPOSITORY='anemiaiaback'
export SERVICE='anemiaiaback'
gcloud config set project "$PROJECT_ID"

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com

gcloud artifacts repositories create "$REPOSITORY" \
  --repository-format=docker \
  --location="$REGION" \
  --description='AnemiaIA backend images'
```

Create a dedicated runtime identity:

```bash
gcloud iam service-accounts create anemiaiaback-runtime \
  --display-name='AnemiaIA Cloud Run runtime'
export RUNTIME_SA="anemiaiaback-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
```

### 2. Use the Supabase transaction pooler

In Supabase Dashboard, open **Connect**, select **Transaction pooler**, and copy its host, port, database, and user. Use port `6543`, not the direct database endpoint: Cloud Run is serverless and the direct endpoint may require IPv6. The repository disables psycopg prepared statements (`prepare_threshold=None`) for transaction-pooler compatibility and enables connection pre-ping. Keep `DB_SSLMODE=require`.

### 3. Create secrets

Never upload `.env` or paste secret values into `cloudbuild.yaml`. Create each secret from a local file or an interactive command that does not leave the value in shell history. Secret names expected by the default build configuration are:

- `anemiaiaback-api-key` (at least 32 random characters)
- `anemiaiaback-db-password`
- `anemiaiaback-s3-access-key`
- `anemiaiaback-s3-secret-key`

Example for a prepared file, repeated for each secret:

```bash
gcloud secrets create anemiaiaback-api-key --replication-policy=automatic
gcloud secrets versions add anemiaiaback-api-key --data-file=/secure/path/api-key.txt
```

Grant only the runtime service account access to these four secrets:

```bash
for SECRET in anemiaiaback-api-key anemiaiaback-db-password anemiaiaback-s3-access-key anemiaiaback-s3-secret-key; do
  gcloud secrets add-iam-policy-binding "$SECRET" \
    --member="serviceAccount:${RUNTIME_SA}" \
    --role='roles/secretmanager.secretAccessor'
done
```

### 4. Grant build/deploy permissions

Find the Cloud Build service account in **Cloud Build > Settings** and grant it permission to deploy Cloud Run, use the runtime identity, and push to Artifact Registry. Prefer the dedicated Cloud Build service account shown by your project instead of assuming its name. Required roles are `roles/run.admin`, `roles/iam.serviceAccountUser` on the runtime service account, and `roles/artifactregistry.writer` on the repository. Keep the scope at the individual service account/repository where the Console permits it.

### 5. Configure and submit the build

Do not commit environment-specific identifiers. Pass them as substitutions. Replace the Supavisor values and Supabase project reference:

```bash
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions="_REGION=${REGION},_REPOSITORY=${REPOSITORY},_SERVICE=${SERVICE},_RUNTIME_SERVICE_ACCOUNT=${RUNTIME_SA},_DB_HOST=aws-0-us-west-1.pooler.supabase.com,_DB_PORT=6543,_DB_NAME=AnemiaIA,_DB_USER=your-supavisor-user,_S3_ENDPOINT=https://your-project-ref.storage.supabase.co/storage/v1/s3,_S3_REGION=us-west-2,_S3_BUCKET=ImagesProcesed" \
  .
```

The deployment is public at the Cloud Run transport layer so Postman and the Android test app can call it, but `/api/v1` is rejected unless `X-API-Key` is valid. The conservative Cloud Run settings are 1 CPU, 2 GiB memory, concurrency 1, minimum 0, maximum 1, and a 120-second timeout. Minimum 0 avoids idle instance cost; maximum 1 limits cost but also limits throughput and availability, which is appropriate only for this test phase.

### 6. Verify with Postman

Obtain the service URL without exposing secrets:

```bash
SERVICE_URL="$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')"
curl "$SERVICE_URL/health"
```

In Postman create `POST {{service_url}}/api/v1/captures`, add header `X-API-Key: {{api_key}}`, choose **Body > form-data**, and add `image` as **File**, plus text fields `dni`, `sex`, and `age`. A successful request returns HTTP 201. A missing or invalid key returns HTTP 401. Confirm the PNG object exists in the private `ImagesProcesed` bucket and the matching row exists in `patients`.

Rotate the Supabase S3 credentials that were previously shared in chat before deployment, then put only the rotated values in Secret Manager.
