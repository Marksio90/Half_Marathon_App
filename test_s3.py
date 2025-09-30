import os
from botocore.config import Config
import boto3

# ---- KONFIG ----
bucket   = os.environ.get("DO_SPACES_BUCKET")           # Np. my-bucket
region   = os.environ.get("DO_SPACES_REGION", "fra1")   # Np. fra1 / ams3 / nyc3
endpoint = f"https://{region}.digitaloceanspaces.com"
key      = "models/halfmarathon_model_latest.pkl"       # DOKŁADNIE jak w kodzie

access_key = os.environ.get("DO_SPACES_KEY")
secret_key = os.environ.get("DO_SPACES_SECRET")

print(f"Endpoint: {endpoint}")
print(f"Bucket:   {bucket}")
print(f"Key:      {key}")
print(f"Region:   {region}")

if not all([bucket, access_key, secret_key]):
    raise SystemExit("❌ Brakuje envów: DO_SPACES_BUCKET/KEY/SECRET")

# Klient S3 kompatybilny ze Spaces (podpis v4)
s3 = boto3.client(
    "s3",
    region_name=region,
    endpoint_url=endpoint,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
)

# 1) HEAD (czy obiekt istnieje i czy mamy uprawnienia?)
try:
    resp = s3.head_object(Bucket=bucket, Key=key)
    print("✅ HEAD OK: Content-Length =", resp.get("ContentLength"))
except Exception as e:
    print("⚠️ HEAD failed:", e)

# 2) LIST (pokazuje, co widać pod prefixem)
prefix = "models/"
try:
    resp = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=20)
    count = resp.get("KeyCount", 0)
    print(f"ℹ️ LIST s3://{bucket}/{prefix}  KeyCount={count}")
    for obj in resp.get("Contents", [])[:10]:
        print(" -", obj["Key"], obj["Size"], "bytes")
except Exception as e:
    print("⚠️ LIST failed:", e)
