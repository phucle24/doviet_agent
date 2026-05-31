#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root: sudo bash deploy/install_systemd.sh"
  exit 1
fi

install -m 0644 deploy/systemd/*.service /etc/systemd/system/
install -m 0644 deploy/systemd/*.timer /etc/systemd/system/

systemctl daemon-reload
systemctl disable --now 'fb-animal-agent-*' 2>/dev/null || true
systemctl disable --now doviet-agent-publish-morning.timer 2>/dev/null || true
systemctl disable --now doviet-agent-publish-evening.timer 2>/dev/null || true
systemctl enable --now doviet-agent-web.service
systemctl enable --now doviet-agent-ensure.timer
systemctl enable --now doviet-agent-poll-batch.timer
systemctl enable --now doviet-agent-publish-due.timer
systemctl enable --now doviet-agent-publish-answers.timer

systemctl list-timers 'doviet-agent-*'
