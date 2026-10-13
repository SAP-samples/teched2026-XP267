#!/usr/bin/env bash
#
# upload_bronze.sh — stage the non-SAP Vertex MES CSVs into the shared S3 bucket
# as the bronze/ layout that the Exercise 1 OTIF (manufacturing) track expects.
#
# This is a ONE-TIME, pre-session author/lab-admin task. Students never run it;
# they only read the data from Dremio. Run it once, up front, so all raw data is
# staged before the session (see infra/README.md — "stage once, transform progressively").
#
# Each feed goes into its OWN folder under bronze/ so Dremio promotes it as a
# single dataset:  bronze/<table>/<table>.csv
#
# Usage:
#   ./upload_bronze.sh s3://my-teched-bucket            # upload under bronze/
#   ./upload_bronze.sh s3://my-teched-bucket my-prefix  # upload under my-prefix/bronze/
#   DRY_RUN=1 ./upload_bronze.sh s3://my-teched-bucket  # print what would happen
#
# Requires: awscli v2, configured credentials with s3:PutObject on the bucket.

set -euo pipefail

BUCKET="${1:-}"
BASE_PREFIX="${2:-}"

if [[ -z "$BUCKET" ]]; then
  echo "ERROR: pass the target bucket, e.g.  ./upload_bronze.sh s3://my-teched-bucket" >&2
  exit 1
fi

# Normalize: strip trailing slash from bucket; build the bronze/ destination root.
BUCKET="${BUCKET%/}"
if [[ -n "$BASE_PREFIX" ]]; then
  DEST_ROOT="${BUCKET}/${BASE_PREFIX%/}/bronze"
else
  DEST_ROOT="${BUCKET}/bronze"
fi

# Resolve the data directory relative to this script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${SCRIPT_DIR}/../data/otif-synth-data"

# The seven NON-SAP (Vertex MES) feeds. sap_work_center.csv is intentionally
# EXCLUDED — it is the SAP side (the workcenter data product), not non-SAP data.
FEEDS=(
  work_order
  equipment
  downtime_event
  quality_event
  production_count
  oee_snapshot
  ground_truth_xref
)

AWS_CP=(aws s3 cp)
[[ "${DRY_RUN:-0}" == "1" ]] && AWS_CP=(echo "[dry-run] aws s3 cp")

echo "Staging non-SAP MES CSVs:"
echo "  from : ${DATA_DIR}"
echo "  to   : ${DEST_ROOT}/<table>/"
echo

for feed in "${FEEDS[@]}"; do
  src="${DATA_DIR}/${feed}.csv"
  dst="${DEST_ROOT}/${feed}/${feed}.csv"
  if [[ ! -f "$src" ]]; then
    echo "ERROR: missing source file: $src" >&2
    exit 1
  fi
  "${AWS_CP[@]}" "$src" "$dst"
done

echo
echo "Done. In Dremio, point your S3 source at ${DEST_ROOT%/bronze}/ and format each"
echo "bronze/<table>/ folder as a CSV dataset (header on first line). Then the Exercise 1 OTIF track's"
echo "CREATE TABLE ... AS SELECT converts them to managed Iceberg."