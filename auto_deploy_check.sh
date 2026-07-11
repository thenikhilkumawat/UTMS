#!/bin/bash
cd /home/ubuntu/website || exit 1
git fetch origin website --quiet 2>/dev/null
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/website)
if [ "$LOCAL" != "$REMOTE" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] New commits found — deploying..."
    git pull origin website
    sudo systemctl restart website
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Deployed successfully."
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] No changes."
fi
