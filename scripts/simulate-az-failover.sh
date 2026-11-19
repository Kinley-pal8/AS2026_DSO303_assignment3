#!/usr/bin/env bash
# Simulates losing the database's Availability Zone: forces an RDS Multi-AZ failover while
# polling the API's deep health check (which queries PostgreSQL through RDS Proxy) every 2 s.
# Output is a timeline saved to evidence/ and shown in a screenshot.
set -euo pipefail
cd "$(dirname "$0")/../infra"

APP_URL=$(terraform output -raw app_url)
DB_ID=$(terraform output -raw db_instance_id)
LOG="../evidence/az-failover-$(date +%Y%m%d-%H%M%S).log"

az_of() { aws rds describe-db-instances --db-instance-identifier "$DB_ID" \
  --query 'DBInstances[0].[AvailabilityZone,SecondaryAvailabilityZone]' --output text; }

echo "Before: primary/standby AZ = $(az_of)" | tee "$LOG"
aws rds reboot-db-instance --db-instance-identifier "$DB_ID" --force-failover >/dev/null
echo "$(date +%T) forced failover requested" | tee -a "$LOG"

BEFORE=$(az_of | awk '{print $1}')
down_since=""; up_at=""
for i in $(seq 1 150); do
  rm -f /tmp/health.json
  code=$(curl -s -m 5 -o /tmp/health.json -w "%{http_code}" "$APP_URL/api/health?deep=1" || true)
  [[ "$code" == "000" ]] && echo "{\"error\": \"timeout or connection reset\"}" > /tmp/health.json
  echo "$(date +%T) HTTP $code $(cat /tmp/health.json 2>/dev/null)" | tee -a "$LOG"
  now=$(date +%s)
  if [[ "$code" != "200" && -z "$down_since" ]]; then down_since=$now; fi
  if [[ "$code" == "200" && -n "$down_since" && -z "$up_at" ]]; then up_at=$now; fi
  status=$(aws rds describe-db-instances --db-instance-identifier "$DB_ID" --query 'DBInstances[0].DBInstanceStatus' --output text)
  if [[ "$status" == "available" && ( -n "$up_at" || ( -z "$down_since" && $i -gt 30 ) ) ]]; then break; fi
  sleep 2
done

if [[ -n "$down_since" && -n "$up_at" ]]; then
  echo "API outage (first failed to first successful health check): $(( up_at - down_since )) s" | tee -a "$LOG"
else
  echo "No failed health check observed (outage shorter than the 2 s polling interval)" | tee -a "$LOG"
fi

# RDS can take a few minutes to report the new primary AZ after the failover itself.
for i in $(seq 1 30); do
  [[ "$(az_of | awk '{print $1}')" != "$BEFORE" ]] && break
  sleep 10
done
echo "After: primary/standby AZ = $(az_of)" | tee -a "$LOG"
aws rds describe-events --source-identifier "$DB_ID" --source-type db-instance --duration 30 \
  --query 'Events[].[Date,Message]' --output text | grep -i -E "failover|multi-az" | tee -a "$LOG" || true
echo "Saved $LOG"
