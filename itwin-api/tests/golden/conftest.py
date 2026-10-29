def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "sety_golden: эталонные расчёты sety на копиях БД (долго; запуск: SETY_GOLDEN=1, "
        "см. docs/sety-golden-reference.md)",
    )
