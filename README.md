# Google Speech-to-Text Translation Tool

This tool reads Google Speech-to-Text JSON output files from Google Cloud Storage, extracts the Spanish transcription, translates it to English using Google Cloud Translation API v3, and stores both Spanish and English text files back to GCS.

## Features

- Reads Speech-to-Text JSON files from GCS buckets
- Handles large transcriptions by chunking text for translation (up to 25,000 characters per chunk)
- Uses Translation API v3 with Neural Machine Translation for high-quality translations
- Saves both Spanish and English text files
- Runs in an isolated Docker container
- Supports processing single files or entire bucket prefixes

## Prerequisites

1. **GCP Service Account**: You need a service account with the following permissions:
   - Storage Object Viewer (to read JSON files)
   - Storage Object Creator (to write text files)
   - Cloud Translation API Editor (for v3 API)

2. **Service Account Key**: Download the JSON key file for your service account

3. **GCP Project ID**: Required for Translation API v3

## Setup

### 1. Add Your GCP Credentials

Place your service account JSON key file in this directory and name it `gcp-credentials.json`

### 2. Start the Docker Container

```bash
docker-compose up -d
```

This builds the image (if needed) and starts the container in the background.

### 3. Exec into the Container

```bash
docker-compose exec translate bash
```

Now you're inside the container and can run the script!

## Usage

#### Process All JSON Files in a Bucket

```bash
python translate_transcripts.py \
  --bucket YOUR_BUCKET_NAME \
  --project-id YOUR_GCP_PROJECT_ID
```

#### Process JSON Files in a Specific Folder/Prefix

```bash
python translate_transcripts.py \
  --bucket YOUR_BUCKET_NAME \
  --project-id YOUR_GCP_PROJECT_ID \
  --input-prefix "speech-to-text-output/" \
  --output-prefix "translated/"
```

#### Process a Single File

```bash
python translate_transcripts.py \
  --bucket YOUR_BUCKET_NAME \
  --project-id YOUR_GCP_PROJECT_ID \
  --file "path/to/your/file.json" \
  --output-prefix "translated/"
```

### Command-Line Arguments

- `--bucket`: **(Required)** GCS bucket name
- `--project-id`: **(Required)** GCP Project ID
- `--input-prefix`: Folder path for input JSON files (default: root of bucket)
- `--output-prefix`: Folder path for output text files (default: "translated")
- `--file`: Process a single specific file instead of all files

## Output

For each processed JSON file, the script creates two text files:

1. `{output-prefix}/{filename}_spanish.txt` - Original Spanish transcription
2. `{output-prefix}/{filename}_english.txt` - English translation using v3 API

## Example

If you have a file `gs://my-bucket/transcripts/interview_001.json`:

```bash
python translate_transcripts.py \
  --bucket my-bucket \
  --project-id my-gcp-project \
  --file "transcripts/interview_001.json" \
  --output-prefix "translations"
```

This will create:
- `gs://my-bucket/translations/interview_001_spanish.txt`
- `gs://my-bucket/translations/interview_001_english.txt`

## Handling Large Transcriptions

The script automatically handles large transcriptions by:
- Chunking text into ~25,000 character segments (v3 API supports larger chunks)
- Translating each chunk separately
- Reassembling the translated chunks

This ensures the Google Translation API limits are not exceeded.

## Translation Quality

The script uses Translation API v3 with Neural Machine Translation (NMT) for:
- Context-aware translations
- Natural-sounding language
- Better handling of idioms and cultural references
- More accurate technical terminology

## Troubleshooting

### Authentication Errors

If you see authentication errors, verify that:
1. Your service account key file is correctly mounted
2. The `GOOGLE_APPLICATION_CREDENTIALS` environment variable is set correctly
3. Your service account has the necessary permissions

### No Transcript Found

If the script reports "No transcript found", check that your JSON file follows the Google Speech-to-Text output format with a `results` array containing `alternatives`.
