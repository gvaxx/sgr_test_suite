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

## Базовый LLM-пайплайн

В модуле `models.pipeline` есть утилиты для работы с OpenAI-совместимыми моделями. Самый простой вариант — использовать `ChatPipeline`, который принимает клиента `OpenAIClient` и пару промптов (системный необязателен). Плейсхолдеры в пользовательском промпте подставляются из аргументов `run`:

```python
from models.pipeline import ChatPipeline, PromptTemplate
from sgr.llm import LLMClientConfig, OpenAIClient

client = OpenAIClient(LLMClientConfig(api_key="sk-..."))
pipeline = ChatPipeline(
    client=client,
    prompt=PromptTemplate(
        system="Ты помощник по путешествиям.",
        user="Подскажи, что посмотреть в городе {city}?",
    ),
)

print(pipeline.run(city="Лиссабон"))
```

### Пример готового пайплайна и тестов

Каталог `sgr/pipelines` хранит примеры полностью собранных пайплайнов. Для
маршрутизации обращений используется модуль `sgr.pipelines.routing`, а для
разбиения сообщений на отдельные заказы — `sgr.pipelines.splitter`. В обоих
подкаталогах указаны промпты, схемы ответа и примерные наборы тестов
`test_cases.json`. Внутри каждой папки также зарезервирован каталог `reports/` для хранения выгруженных отчётов CLI/UI (он будет
создаваться автоматически, но в репозитории лежит пустой `.gitkeep`).

```
sgr/
└── pipelines/
    ├── routing/
    │   ├── __init__.py
    │   ├── pipeline.py        # OrderIssuePipeline с промптами и схемой ответа
    │   ├── reports/           # Сюда можно складывать JSON-отчёты после прогонов
    │   └── test_cases.json    # Пример универсальных тест-кейсов для маршрутизации
    └── splitter/
        ├── __init__.py
        ├── pipeline.py        # ConversationSplitterPipeline с промптом и схемой JSON
        ├── reports/           # Отчёты по прогону splitter-тестов
        └── test_cases.json    # Пример кейсов для выделения нескольких заказов
```

`test_cases.json` использует ту же схему, что и CLI (`id`, `params`,
`expected_output`, опционально `description` и `comparator`).

### Кастомные компараторы

По умолчанию результаты сравниваются оператором `==`. Теперь можно задать
кастомное поведение:

- **На уровне раннера/Gradio**: передайте в `TestRunner` или `launch_gradio_app`
  аргумент `comparator` (один компаратор для всех тестов) или словарь
  `comparators` с именованными функциями.
- **На уровне пайплайна**: добавьте атрибут `default_comparator` или словарь
  `comparators` в экземпляр/класс пайплайна. Они используются, если нет
  переопределения в раннере или тесте.
- **На уровне тест-кейса**: в JSON можно прописать поле `"comparator"` с
  именем функции из реестра (раннера или пайплайна). Также можно передать
  callable напрямую в `TestCase` при сборке тестов в коде.

Приоритеты: сначала берётся компаратор тест-кейса, затем реестр раннера,
затем `default_comparator` пайплайна и, наконец, сравнение через `==`.

*Пример:* для `ConversationSplitterPipeline` по умолчанию используется
компаратор, который проверяет только количество выделенных заказов и флаг
`has_request_several_orders`, не сравнивая `thinking`.

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

По завершении будет выведена сводка по количеству тестов и точности. Опционально можно сохранить полный отчёт в JSON:

- через `--output path/to/report.json` — в конкретный файл;
- через `--report-dir ./reports` — в указанный каталог с автогенерацией имени файла.
