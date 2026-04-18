# .claude/ops — TCGInvest Control Plane

## What lives where and why

### Hetzner (prod) — /root/.openclaw/.claude/ops/
Only scripts that must execute locally against prod code/venv:

| Script | Purpose |
|---|---|
| build-api.sh | pip install + py_compile syntax check |
| build-frontend.sh | npm run build |
| test.sh | pytest in venv |

### Paperclip — /home/jaytee/ops/
All orchestration and control scripts. These SSH *into* Hetzner rather than
running on it, so a compromised prod server cannot self-trigger destructive ops:

| Script | Purpose |
|---|---|
| deploy-prod.sh | Full gated deploy: test → build → restart → verify |
| deploy-staging.sh | Deploy staging branch to preprod |
| health-check.sh | External HTTP probe of prod endpoints |
| sync-brain.sh | Pull CLAUDE.md from Hetzner → Paperclip (runs every 6h via cron) |

## CI → Discord loop: the missing piece

The GitHub Actions workflow runs on GitHub-hosted runners which cannot reach
n8n on Tailscale (100.107.74.24:5678). The fix is a self-hosted runner on
Paperclip, which *is* on the Tailscale network.

### Register a self-hosted runner on Paperclip

1. Go to your GitHub repo → Settings → Actions → Runners → New self-hosted runner
2. Select: Linux / x64
3. Copy the token GitHub shows you, then run on Paperclip:

```bash
mkdir -p /home/jaytee/github-runner && cd /home/jaytee/github-runner

# Download runner (check GitHub for latest version)
curl -o runner.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.322.0/actions-runner-linux-x64-2.322.0.tar.gz
tar xzf runner.tar.gz

# Configure (replace YOUR_REPO and YOUR_TOKEN)
./config.sh \
  --url https://github.com/YOUR_ORG/YOUR_REPO \
  --token YOUR_RUNNER_TOKEN \
  --name paperclip-runner \
  --labels tailscale,paperclip \
  --unattended

# Install and start as a service
sudo ./svc.sh install
sudo ./svc.sh start
```

4. In .github/workflows/agile-cycle.yml, change:
   ```yaml
   runs-on: ubuntu-latest
   ```
   to:
   ```yaml
   runs-on: [self-hosted, paperclip]
   ```

5. Add this step back to the notify section (it will now reach Tailscale):
   ```yaml
   - name: Notify n8n
     if: always()
     run: |
       curl -s -X POST http://100.107.74.24:5678/webhook/tcg-ci-result \
         -H "Content-Type: application/json" \
         -d '{
           "status": "${{ job.status }}",
           "branch": "${{ github.ref_name }}",
           "commit": "${{ github.sha }}",
           "commit_short": "${{ github.sha }}"[0:7],
           "actor": "${{ github.actor }}",
           "run_url": "https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }}"
         }'
   ```

## n8n Variables alternative

n8n Variables require a paid plan. All Discord webhook URLs are instead
hardcoded directly into workflow nodes using the stored Discord credential
(credential ID: NaIqE62BFu2tIwJG — "Discord Webhook account").

If the Discord webhook URL ever changes, update it by running on Paperclip:
```bash
# Re-run the patch script with the new URL
python3 /home/jaytee/ops/patch-discord-url.py NEW_WEBHOOK_URL
```
