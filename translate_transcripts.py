#!/usr/bin/env python3
"""
Script to read Google Speech-to-Text JSON files from GCS,
translate Spanish transcriptions to English, and save back to GCS.
"""

import json
import os
import argparse
from google.cloud import storage
from google.cloud import translate_v3


def extract_transcript_from_json(json_data):
    """
    Extract transcript text from Google Speech-to-Text JSON output.
    Handles both standard and long-running operation formats.
    """
    transcript_parts = []

    # Handle different JSON formats
    if 'results' in json_data:
        # Standard format
        for result in json_data.get('results', []):
            if 'alternatives' in result and len(result['alternatives']) > 0:
                transcript_parts.append(result['alternatives'][0].get('transcript', ''))
    elif 'response' in json_data and 'results' in json_data['response']:
        # Long-running operation format
        for result in json_data['response']['results']:
            if 'alternatives' in result and len(result['alternatives']) > 0:
                transcript_parts.append(result['alternatives'][0].get('transcript', ''))

    return ' '.join(transcript_parts).strip()


def translate_text_chunked(text, target_language='en', source_language='es',
                          chunk_size=5000, project_id=None):
    """
    Translate text in chunks using Translation API v3.

    Args:
        text: Text to translate
        target_language: Target language code (default: 'en')
        source_language: Source language code (default: 'es')
        chunk_size: Maximum chunk size in characters
        project_id: GCP project ID (required for v3 API)
    """
    if not project_id:
        raise ValueError("project_id is required for Translation API v3")

    client = translate_v3.TranslationServiceClient()
    location = "global"
    parent = f"projects/{project_id}/locations/{location}"

    # v3 can handle larger chunks (up to 30k codepoints)
    max_chunk = min(chunk_size, 25000)

    # Split text into chunks
    chunks = []
    current_chunk = []
    current_length = 0
    words = text.split()

    for word in words:
        word_length = len(word) + 1
        if current_length + word_length > max_chunk and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_length = word_length
        else:
            current_chunk.append(word)
            current_length += word_length

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    # Translate each chunk
    translated_chunks = []
    for i, chunk in enumerate(chunks):
        print(f"  Translating chunk {i+1}/{len(chunks)} ({len(chunk)} chars)...")

        response = client.translate_text(
            request={
                "parent": parent,
                "contents": [chunk],
                "mime_type": "text/plain",
                "source_language_code": source_language,
                "target_language_code": target_language,
            }
        )

        translated_chunks.append(response.translations[0].translated_text)

    return ' '.join(translated_chunks)


def process_file(bucket_name, input_blob_path, output_prefix='translated', project_id=None):
    """
    Process a single JSON file: extract transcript, translate, and save both Spanish and English.
    """
    print(f"\nProcessing: gs://{bucket_name}/{input_blob_path}")

    # Initialize GCS client
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # Download JSON file
    print("  Downloading JSON file...")
    blob = bucket.blob(input_blob_path)
    json_content = blob.download_as_text()
    json_data = json.loads(json_content)

    # Extract transcript
    print("  Extracting transcript...")
    spanish_text = extract_transcript_from_json(json_data)

    if not spanish_text:
        print("  WARNING: No transcript found in JSON file!")
        return

    print(f"  Extracted {len(spanish_text)} characters")

    # Generate output paths
    base_name = os.path.splitext(os.path.basename(input_blob_path))[0]
    spanish_output_path = f"{output_prefix}/{base_name}_spanish.txt"
    english_output_path = f"{output_prefix}/{base_name}_english.txt"

    # Save original Spanish transcript
    print(f"  Saving Spanish transcript to: gs://{bucket_name}/{spanish_output_path}")
    spanish_blob = bucket.blob(spanish_output_path)
    spanish_blob.upload_from_string(spanish_text, content_type='text/plain; charset=utf-8')

    # Translate to English using v3 API
    print("  Translating Spanish to English...")
    english_text = translate_text_chunked(spanish_text, project_id=project_id)

    # Save English translation
    print(f"  Saving English translation to: gs://{bucket_name}/{english_output_path}")
    english_blob = bucket.blob(english_output_path)
    english_blob.upload_from_string(english_text, content_type='text/plain; charset=utf-8')

    print("  ✓ Processing complete!")
    return spanish_output_path, english_output_path


def process_bucket(bucket_name, input_prefix='', output_prefix='translated',
                   file_pattern='*.json', project_id=None):
    """
    Process all JSON files in a GCS bucket/prefix.
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # List all JSON files
    print(f"Searching for JSON files in gs://{bucket_name}/{input_prefix}")
    blobs = list(bucket.list_blobs(prefix=input_prefix))
    json_files = [blob.name for blob in blobs if blob.name.endswith('.json')]

    if not json_files:
        print(f"No JSON files found in gs://{bucket_name}/{input_prefix}")
        return

    print(f"Found {len(json_files)} JSON file(s)")

    for json_file in json_files:
        try:
            process_file(bucket_name, json_file, output_prefix, project_id)
        except Exception as e:
            print(f"ERROR processing {json_file}: {str(e)}")
            continue


def main():
    parser = argparse.ArgumentParser(
        description='Translate Google Speech-to-Text transcriptions from Spanish to English using Translation API v3'
    )
    parser.add_argument(
        '--bucket',
        required=True,
        help='GCS bucket name'
    )
    parser.add_argument(
        '--input-prefix',
        default='',
        help='Prefix/folder path for input JSON files (default: root of bucket)'
    )
    parser.add_argument(
        '--output-prefix',
        default='translated',
        help='Prefix/folder path for output text files (default: "translated")'
    )
    parser.add_argument(
        '--file',
        help='Process a single file instead of all files in prefix'
    )
    parser.add_argument(
        '--project-id',
        required=True,
        help='GCP Project ID (required for Translation API v3)'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Google Speech-to-Text Translation Tool (v3 API)")
    print("=" * 60)

    if args.file:
        # Process single file
        process_file(args.bucket, args.file, args.output_prefix, args.project_id)
    else:
        # Process all files in prefix
        process_bucket(args.bucket, args.input_prefix, args.output_prefix,
                      project_id=args.project_id)

    print("\n" + "=" * 60)
    print("All processing complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()
