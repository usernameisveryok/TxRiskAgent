from __future__ import annotations

import json
import sys

from signshield.env import load_dotenv


def test_load_dotenv_reads_simple_values_and_quotes(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                "# local secrets",
                "TENDERLY_ACCOUNT_SLUG=eggry",
                'TENDERLY_PROJECT_SLUG="project"',
                "TENDERLY_ACCESS_KEY='replace_me'",
                "INVALID-KEY=ignored",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("TENDERLY_ACCOUNT_SLUG", raising=False)
    monkeypatch.delenv("TENDERLY_PROJECT_SLUG", raising=False)
    monkeypatch.delenv("TENDERLY_ACCESS_KEY", raising=False)

    load_dotenv(env_path)

    import os

    assert os.getenv("TENDERLY_ACCOUNT_SLUG") == "eggry"
    assert os.getenv("TENDERLY_PROJECT_SLUG") == "project"
    assert os.getenv("TENDERLY_ACCESS_KEY") == "replace_me"
    assert os.getenv("INVALID-KEY") is None


def test_load_dotenv_does_not_override_existing_env(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("TENDERLY_ACCOUNT_SLUG=from_file\n", encoding="utf-8")
    monkeypatch.setenv("TENDERLY_ACCOUNT_SLUG", "from_env")

    load_dotenv(env_path)

    import os

    assert os.getenv("TENDERLY_ACCOUNT_SLUG") == "from_env"


def test_cli_loads_dotenv_and_cli_args_override(tmp_path, monkeypatch, capsys) -> None:
    from signshield import cli

    input_file = tmp_path / "tx.json"
    input_file.write_text(
        json.dumps({"chainId": "eip155:1", "transaction": {"from": "0x0000000000000000000000000000000000000001", "to": "0x0000000000000000000000000000000000000002", "value": "0x0", "data": "0x"}}),
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "TENDERLY_ACCOUNT_SLUG=from_file",
                "TENDERLY_PROJECT_SLUG=project",
                "TENDERLY_ACCESS_KEY=file_key",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TENDERLY_ACCOUNT_SLUG", raising=False)
    monkeypatch.delenv("TENDERLY_PROJECT_SLUG", raising=False)
    monkeypatch.delenv("TENDERLY_ACCESS_KEY", raising=False)
    captured = {}

    def fake_analyze_transaction(payload, input_ref, *, options, token_metadata_provider, **kwargs):
        captured["options"] = options
        return {
            "schemaVersion": "signshield-risk/v0.2",
            "inputRef": input_ref,
            "verdict": {},
            "summary": "",
            "intent": {},
            "assetImpact": [],
            "riskFactors": [],
            "evidence": {},
            "recommendation": "",
        }

    monkeypatch.setattr(cli, "analyze_transaction", fake_analyze_transaction)
    monkeypatch.setattr(sys, "argv", ["analyze_evm_tx.py", str(input_file), "--live", "--tenderly-account", "from_cli"])

    assert cli.main() == 0

    assert captured["options"].tenderly_account == "from_cli"
    assert captured["options"].tenderly_project == "project"
    assert captured["options"].tenderly_access_key == "file_key"
    assert capsys.readouterr().out


def test_check_integrations_loads_dotenv_without_exposing_key(tmp_path, monkeypatch, capsys) -> None:
    import check_integrations

    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "TENDERLY_ACCOUNT_SLUG=eggry",
                "TENDERLY_PROJECT_SLUG=project",
                "TENDERLY_ACCESS_KEY=fake_test_key",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TENDERLY_ACCOUNT_SLUG", raising=False)
    monkeypatch.delenv("TENDERLY_PROJECT_SLUG", raising=False)
    monkeypatch.delenv("TENDERLY_ACCESS_KEY", raising=False)

    class FakeTenderly:
        def __init__(self, account, project, access_key):
            assert account == "eggry"
            assert project == "project"
            assert access_key == "fake_test_key"

        def simulate(self, chain_id, tx):
            return {"status": "ok", "provider": "tenderly", "facts": []}

    class FakeContract:
        def __init__(self, api_key, blockscout_base_url):
            pass

        def inspect(self, chain_id, address):
            return {"etherscan": {"status": "config_missing"}}

    class FakeThreat:
        def inspect(self, chain_id, addresses, origin):
            return {"status": "ok", "matches": []}

    monkeypatch.setattr(check_integrations, "TenderlySimulationAdapter", FakeTenderly)
    monkeypatch.setattr(check_integrations, "CompositeContractReputationAdapter", FakeContract)
    monkeypatch.setattr(check_integrations, "CompositeThreatIntelAdapter", lambda: FakeThreat())
    monkeypatch.setattr(check_integrations, "check_public_rpc_endpoints", lambda: [])

    assert check_integrations.main() == 0
    output = capsys.readouterr().out
    assert "fake_test_key" not in output
    assert '"tenderly"' in output
