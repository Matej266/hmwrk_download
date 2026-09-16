from logger import write_log


def test_write_log_creates_csv_with_rows(tmp_path):
    rows = [
        {
            "student": "John Smith",
            "filename": "2026-03-02_John Smith.pdf",
            "action": "downloaded",
            "bucket": "2026-03-02",
        }
    ]

    log_path = write_log(rows, log_dir=str(tmp_path))

    assert log_path.exists()
    content = log_path.read_text()
    assert "John Smith" in content
    assert "downloaded" in content


def test_write_log_handles_non_latin_names(tmp_path):
    rows = [
        {
            "student": "Иван Иванов",
            "filename": "2026-09-14_Иван Иванов.pdf",
            "action": "downloaded",
            "bucket": "2026-09-14",
        }
    ]

    log_path = write_log(rows, log_dir=str(tmp_path))

    content = log_path.read_text(encoding="utf-8")
    assert "Иван Иванов" in content


def test_write_log_prints_summary_to_console(tmp_path, capsys):
    rows = [{"student": "John Smith", "filename": "a.pdf", "action": "downloaded", "bucket": "2026-03-02"}]

    write_log(rows, log_dir=str(tmp_path))

    captured = capsys.readouterr()
    assert "downloaded" in captured.out


def test_write_log_handles_empty_rows(tmp_path, capsys):
    log_path = write_log([], log_dir=str(tmp_path))

    assert log_path.exists()
    captured = capsys.readouterr()
    assert "No actions taken." in captured.out
