import os

import pytest
import requests


APIDECK_BASE_URL = "https://unify.apideck.com"


def _get_env(name: str) -> str:
    value = os.environ.get(name, "")
    assert value, f"Required environment variable {name} is not set."
    return value


def _apideck_headers() -> dict:
    return {
        "Authorization": f"Bearer {_get_env('APIDECK_API_KEY')}",
        "x-apideck-app-id": _get_env("APIDECK_APP_ID"),
        "x-apideck-consumer-id": _get_env("APIDECK_CONSUMER_ID"),
        "x-apideck-service-id": "onedrive",
        "Accept": "application/json",
    }


def _iter_all_items(headers: dict):
    url = f"{APIDECK_BASE_URL}/file-storage/files"
    params: dict = {"limit": 200}
    seen: set[str] = set()
    while True:
        response = requests.get(url, headers=headers, params=params, timeout=60)
        assert response.status_code == 200, (
            f"GET /file-storage/files returned {response.status_code}: "
            f"{response.text}"
        )
        body = response.json()
        for item in body.get("data") or []:
            yield item
        cursors = (body.get("meta") or {}).get("cursors") or {}
        next_cursor = cursors.get("next")
        if not next_cursor or next_cursor in seen:
            break
        seen.add(next_cursor)
        params = {"limit": 200, "cursor": next_cursor}


@pytest.fixture(scope="module")
def run_id() -> str:
    return _get_env("ZEALT_RUN_ID")


@pytest.fixture(scope="module")
def expected_names(run_id: str) -> dict:
    return {
        "txt_folder": f"TXT-{run_id}",
        "md_folder": f"MD-{run_id}",
        "txt_files": {f"RAW-{run_id}-{i}.txt" for i in (1, 2, 3)},
        "md_files": {f"RAW-{run_id}-{i}.md" for i in (1, 2, 3)},
    }


@pytest.fixture(scope="module")
def all_items() -> list[dict]:
    headers = _apideck_headers()
    return list(_iter_all_items(headers))


@pytest.fixture(scope="module")
def folder_ids(all_items: list[dict], expected_names: dict) -> dict:
    txt_matches = [
        item
        for item in all_items
        if item.get("type") == "folder"
        and item.get("name") == expected_names["txt_folder"]
    ]
    md_matches = [
        item
        for item in all_items
        if item.get("type") == "folder"
        and item.get("name") == expected_names["md_folder"]
    ]
    assert len(txt_matches) == 1, (
        f"Expected exactly one folder named "
        f"{expected_names['txt_folder']!r} at the drive root, "
        f"found {len(txt_matches)}."
    )
    assert len(md_matches) == 1, (
        f"Expected exactly one folder named "
        f"{expected_names['md_folder']!r} at the drive root, "
        f"found {len(md_matches)}."
    )
    return {
        "txt": txt_matches[0]["id"],
        "md": md_matches[0]["id"],
    }


def _immediate_parent_id(item: dict) -> str | None:
    parents = item.get("parent_folders") or []
    if not parents:
        return None
    # The unified schema lists parent_folders starting from the root, so the
    # immediate parent of the file is the last entry. Some connectors only
    # report the direct parent (single entry).
    return parents[-1].get("id")


def test_txt_folder_exists(folder_ids: dict):
    assert folder_ids["txt"], "TXT-${run_id} folder id was not resolved."


def test_md_folder_exists(folder_ids: dict):
    assert folder_ids["md"], "MD-${run_id} folder id was not resolved."


def test_all_txt_files_moved_into_txt_folder(
    all_items: list[dict], expected_names: dict, folder_ids: dict
):
    txt_folder_id = folder_ids["txt"]
    md_folder_id = folder_ids["md"]
    found_names: set[str] = set()

    for item in all_items:
        name = item.get("name")
        if name not in expected_names["txt_files"]:
            continue
        assert item.get("type") == "file", (
            f"Item named {name!r} should be of type 'file', "
            f"got {item.get('type')!r}."
        )
        parent_id = _immediate_parent_id(item)
        assert parent_id == txt_folder_id, (
            f"Expected file {name!r} to have immediate parent folder id "
            f"{txt_folder_id!r} (TXT-${{run_id}}), got {parent_id!r}."
        )
        assert parent_id != md_folder_id, (
            f"File {name!r} must not be placed inside the MD-${{run_id}} folder."
        )
        found_names.add(name)

    missing = expected_names["txt_files"] - found_names
    assert not missing, (
        f"The following expected .txt files were not found in the drive "
        f"listing: {sorted(missing)}"
    )


def test_all_md_files_moved_into_md_folder(
    all_items: list[dict], expected_names: dict, folder_ids: dict
):
    txt_folder_id = folder_ids["txt"]
    md_folder_id = folder_ids["md"]
    found_names: set[str] = set()

    for item in all_items:
        name = item.get("name")
        if name not in expected_names["md_files"]:
            continue
        assert item.get("type") == "file", (
            f"Item named {name!r} should be of type 'file', "
            f"got {item.get('type')!r}."
        )
        parent_id = _immediate_parent_id(item)
        assert parent_id == md_folder_id, (
            f"Expected file {name!r} to have immediate parent folder id "
            f"{md_folder_id!r} (MD-${{run_id}}), got {parent_id!r}."
        )
        assert parent_id != txt_folder_id, (
            f"File {name!r} must not be placed inside the TXT-${{run_id}} folder."
        )
        found_names.add(name)

    missing = expected_names["md_files"] - found_names
    assert not missing, (
        f"The following expected .md files were not found in the drive "
        f"listing: {sorted(missing)}"
    )
