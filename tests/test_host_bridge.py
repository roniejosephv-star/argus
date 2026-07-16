"""Unit tests for argus.host.bridge."""

from __future__ import annotations

from argus.host.scanner import TargetDevice
from argus.host.bridge import resolve_target


def test_resolve_target(tmp_path, monkeypatch):
    test_file = tmp_path / "targets.json"
    monkeypatch.setattr("argus.host.scanner.get_targets_file_path", lambda: test_file)
    
    t0 = TargetDevice(id=0, hostname="armcreate-pi4", ip="192.168.1.43")
    t1 = TargetDevice(id=1, hostname="jetson-nano", ip="192.168.1.108")
    
    from argus.host.scanner import save_targets
    save_targets([t0, t1])
    
    res0 = resolve_target("0")
    assert res0 is not None and res0.ip == "192.168.1.43"
    
    res_ip = resolve_target("192.168.1.108")
    assert res_ip is not None and res_ip.id == 1
    
    res_host = resolve_target("armcreate-pi4")
    assert res_host is not None and res_host.id == 0
    
    res_none = resolve_target("999")
    assert res_none is None


def test_cli_login(monkeypatch):
    from click.testing import CliRunner
    from argus.cli import cli
    
    run_args = []
    def mock_run(cmd, *args, **kwargs):
        run_args.append(cmd)
        class DummyCompletedProcess:
            returncode = 0
            stdout = "success"
            stderr = ""
        return DummyCompletedProcess()
        
    monkeypatch.setattr("subprocess.run", mock_run)
    monkeypatch.setattr("argus.host.bridge.check_target_status_tunnel", lambda port: True)
    
    runner = CliRunner()
    result = runner.invoke(cli, ["login", "0"])
    assert result.exit_code == 0
    assert any("ssh -t -o StrictHostKeyChecking=no -p 2222 armcreate@127.0.0.1" in cmd for cmd in run_args)

    run_args.clear()
    result_dash = runner.invoke(cli, ["login", "0", "--dash"])
    assert result_dash.exit_code == 0
    assert any("ssh -t -o StrictHostKeyChecking=no -p 2222 armcreate@127.0.0.1 '~/Argus/.venv/bin/argus dash'" in cmd for cmd in run_args)

