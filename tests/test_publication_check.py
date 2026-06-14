from loop_engineering_example.publication import ROOT, scan_text


def test_scan_text_accepts_normal_project_text() -> None:
    path = ROOT / "example.md"

    assert scan_text(path, "A normal experiment observation.") == []


def test_scan_text_detects_machine_specific_home_path() -> None:
    path = ROOT / "example.md"

    assert scan_text(
        path,
        "/Users/" + "example/private/run.json",  # publication-check: allow
    ) == ["example.md:1: possible macOS user path"]


def test_scan_text_accepts_an_explicitly_allowed_example() -> None:
    path = ROOT / "example.md"

    assert (
        scan_text(
            path,
            "/Users/" + "example/private/run.json # publication-check: allow",
        )
        == []
    )
