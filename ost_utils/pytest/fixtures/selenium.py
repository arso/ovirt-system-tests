#
# Copyright oVirt Authors
# SPDX-License-Identifier: GPL-2.0-or-later
#
#

import json

import pytest

from ost_utils import network_utils
from ost_utils.shell import ShellError
from ost_utils.shell import shell

GRID_STARTUP_WAIT_RETRIES = 300


class SeleniumGridError(Exception):
    pass


def _all_nodes_up(nodes_dict):
    for node in nodes_dict:
        if node["availability"] != "UP":
            return False
    return True


def _grid_health_check(hub_url, expected_node_count=None):
    status_url = hub_url + "/status"

    for i in range(GRID_STARTUP_WAIT_RETRIES):
        try:
            status_json = shell(["curl", "-sSL", status_url])
            status_dict = json.loads(status_json)
            if (
                status_dict["value"]["ready"] is True
                and len(status_dict["value"]["nodes"]) == expected_node_count
                and _all_nodes_up(status_dict["value"]["nodes"])
            ):
                break
        except ShellError:
            pass
        time.sleep(0.1)
    else:
        raise SeleniumGridError("Selenium grid didn't start up properly")


@pytest.fixture(scope="session")
def hub_url(ansible_storage, storage_management_ips):
    ansible_storage.systemd(name="selenium-pod", state="started")
    ip = network_utils.ip_to_url(storage_management_ips[0])
    url = f"http://{ip}:4444"
    _grid_health_check(url, 2)
    yield url
    ansible_storage.systemd(name="selenium-pod", state="stopped")
