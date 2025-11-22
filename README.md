# SGR Test Suite

Утилиты для запуска пайплайнов против тест-кейсов и просмотра результатов через Gradio.

## Установка зависимостей

Требуется Python 3.11+. Проект использует `uv`, но можно обойтись стандартным `pip`.

### Вариант с uv
```bash
pip install uv
uv sync
```

### Вариант с pip
```bash
pip install -e .
```

## Быстрый старт (Gradio UI)

1. Создайте пайплайны, реализующие метод `run(**params)` и, желательно, атрибут `name`.
2. Подготовьте тест-кейсы `TestCase` для каждого пайплайна.
3. Соберите их в список `PipelineSuite` и передайте список в `launch_gradio_app` через параметр `pipeline_suites`.

```bash
uv run python - <<'PY'
from dataclasses import dataclass
from sgr.testing import PipelineSuite, TestCase, launch_gradio_app

@dataclass
class EchoPipeline:
    name: str = "Echo"
    def run(self, text: str) -> str:
        return text.upper()

@dataclass
class ReversePipeline:
    name: str = "Reverse"
    def run(self, text: str) -> str:
        return text[::-1]

pipeline_suites = [
    PipelineSuite(
        pipeline=EchoPipeline(),
        test_cases=[
            TestCase(id="echo-1", params={"text": "ping"}, expected_output="PING"),
            TestCase(id="echo-2", params={"text": "pong"}, expected_output="PONG"),
        ],
        description="Проверяет верхний регистр",
    ),
    PipelineSuite(
        pipeline=ReversePipeline(),
        test_cases=[TestCase(id="reverse-1", params={"text": "abc"}, expected_output="cba")],
        description="Разворачивает строки задом наперёд",
    ),
]

launch_gradio_app(
    pipeline_suites=pipeline_suites,
    title="Demo test suite",
    description="Выберите один или несколько пайплайнов, чтобы запустить тесты.",
    share=False,
)
PY
```

В запущенном интерфейсе можно выбрать один или несколько пайплайнов, посмотреть количество тестов и запустить их параллельно в одном клике. Результаты выводятся в сводке и таблице с указанием названия пайплайна для каждого теста.

### Какой параметр использовать в `launch_gradio_app`

- **Несколько пайплайнов.** Передавайте список `PipelineSuite` в параметр `pipeline_suites` (как в примере выше). Именно этот вариант нужен, когда у вас несколько независимых пайплайнов.
- **Один пайплайн.** Можно сократить запись и передать одиночный пайплайн и его тесты через параметры `pipeline` и `test_cases`. Внутри будет создан один `PipelineSuite`.

Во всех случаях внутри UI появится выпадающий список с названиями доступных пайплайнов, так что явный выбор конкретного пайплайна на момент вызова `launch_gradio_app` не требуется.

## Быстрый старт (CLI)

Установите пакет в editable-режиме (`pip install -e .`) или через `uv sync`, после чего станет доступна команда `sgr-test`. Она принимает ссылку на пайплайн в формате `module:attribute` и путь к JSON с тест-кейсами:

```bash
cat > /tmp/pipeline.py <<'PY'
class Echo:
    name = "Echo"

    def run(self, text: str) -> str:
        return text.upper()


pipeline = Echo()
PY

cat > /tmp/cases.json <<'JSON'
[
  {"id": "1", "params": {"text": "ping"}, "expected_output": "PING"},
  {"id": "2", "params": {"text": "pong"}, "expected_output": "PONG"}
]
JSON

uv run sgr-test --pipeline pipeline:pipeline --tests /tmp/cases.json
```

По завершении будет выведена сводка по количеству тестов и точности. Опционально можно сохранить полный отчёт в JSON через `--output path/to/report.json`.
