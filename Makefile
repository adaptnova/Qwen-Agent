.PHONY: install install-systemd health status logs stop

install:
	pip install -r requirements-nova.txt

install-systemd:
	sudo cp systemd/*.service systemd/*.timer /etc/systemd/system/
	sudo systemctl daemon-reload
	sudo systemctl enable --now nova-watchdog.service nova-repo-autopush.service nova-devtools-mcp.service nova-agent.service nova-control.service nova-cleanup.timer

health:
	QWEN_AGENT_DEFAULT_WORKSPACE=${QWEN_AGENT_DEFAULT_WORKSPACE:-/data/nova} python scripts/nova_healthcheck.py

status:
	@echo "Agent:" && systemctl status --no-pager nova-agent.service || true
	@echo "Control:" && systemctl status --no-pager nova-control.service || true

logs:
	journalctl -u nova-agent -f

stop:
	sudo systemctl stop nova-agent.service nova-control.service
