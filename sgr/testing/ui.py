"""Gradio UI for launching test runs and inspecting results."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

import gradio as gr

from .models import TestCase, TestResult, TestRun
from .runner import Pipeline, TestRunner


@dataclass(slots=True)
class PipelineSuite:
    """Контейнер для пайплайна и его тест-кейсов."""

    pipeline: Pipeline
    test_cases: list[TestCase]
    name: str | None = None
    description: str | None = None


def _format_summary(test_run: TestRun) -> str:
    summary = test_run.summary
    return (
        f"**Пайплайн:** {test_run.pipeline_name}\n\n"
        f"**Тестов:** {summary.total}, **Пройдено:** {summary.passed}, **Провалено:** {summary.failed}\n\n"
        f"**Точность:** {summary.accuracy:.0%}\n\n"
        f"**Длительность:** {test_run.duration_seconds:.2f} сек"
    )


def _format_results(test_results: Iterable[TestResult], *, pipeline_name: str) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for result in test_results:
        rows.append(
            [
                pipeline_name,
                result.id,
                result.passed,
                result.output,
                result.expected_output,
                result.error,
                result.duration_seconds,
            ]
        )
    return rows


def _ensure_suites(
    *,
    pipeline: Pipeline | None = None,
    test_cases: Iterable[TestCase] | None = None,
    pipeline_suites: Iterable[PipelineSuite] | None = None,
) -> list[PipelineSuite]:
    if pipeline_suites is not None:
        suites: list[PipelineSuite] = []
        for suite in pipeline_suites:
            name = suite.name or getattr(suite.pipeline, "name", suite.pipeline.__class__.__name__)
            suites.append(
                PipelineSuite(
                    pipeline=suite.pipeline,
                    test_cases=list(suite.test_cases),
                    name=name,
                    description=suite.description,
                )
            )

        return suites

    if pipeline is None or test_cases is None:
        msg = "Нужно передать либо pipeline_suites, либо pipeline и test_cases"
        raise ValueError(msg)

    default_name = getattr(pipeline, "name", pipeline.__class__.__name__)
    return [PipelineSuite(pipeline=pipeline, test_cases=list(test_cases), name=default_name)]


def build_gradio_app(
    *,
    pipeline: Pipeline | None = None,
    test_cases: Iterable[TestCase] | None = None,
    pipeline_suites: Iterable[PipelineSuite] | None = None,
    comparator: Callable[[Any, Any], bool] | None = None,
    title: str = "Sgr Test Suite",
    description: str | None = None,
) -> gr.Blocks:
    """Create a Gradio Blocks application to run tests for one or more pipelines.

    Args:
        pipeline: Пайплайн, реализующий метод ``run`` и атрибут ``name`` (используется для простого случая).
        test_cases: Набор тест-кейсов для запуска (используется для простого случая).
        pipeline_suites: Итерабель со структурами :class:`PipelineSuite` для поддержки нескольких пайплайнов.
        comparator: Пользовательская функция сравнения результатов.
        title: Заголовок UI.
        description: Описание под заголовком.

    Returns:
        Конфигурированный ``gr.Blocks``.
    """

    suites = _ensure_suites(pipeline=pipeline, test_cases=test_cases, pipeline_suites=pipeline_suites)
    runner = TestRunner(comparator=comparator)
    suite_by_name = {suite.name: suite for suite in suites if suite.name is not None}

    def _format_pipeline_info(selected: list[str] | None) -> str:
        if not selected:
            return "Выберите один или несколько пайплайнов, чтобы увидеть детали."

        lines = []
        for name in selected:
            suite = suite_by_name[name]
            lines.append(f"### {name}")
            if suite.description:
                lines.append(suite.description)
            lines.append(f"Тест-кейсов: **{len(suite.test_cases)}**\n")

        return "\n".join(lines)

    def _run_selected(selected: list[str] | None) -> tuple[str, list[list[Any]]]:
        if not selected:
            return "Сначала выберите хотя бы один пайплайн.", []

        summaries: list[str] = []
        all_rows: list[list[Any]] = []
        for name in selected:
            suite = suite_by_name[name]
            test_run = runner.run(pipeline=suite.pipeline, test_cases=suite.test_cases)
            summaries.append(_format_summary(test_run))
            all_rows.extend(_format_results(test_run.results, pipeline_name=name))

        return "\n\n".join(summaries), all_rows

    pipeline_names = list(suite_by_name)

    with gr.Blocks(title=title) as demo:
        gr.Markdown(f"# {title}")
        if description:
            gr.Markdown(description)

        pipeline_selector = gr.Dropdown(
            choices=pipeline_names,
            multiselect=True,
            label="Выберите пайплайн(ы)",
            info="Можно запустить один или сразу несколько пайплайнов",
        )

        info_box = gr.Markdown()
        run_button = gr.Button("Запустить выбранные пайплайны")
        summary_box = gr.Markdown()
        results_table = gr.Dataframe(
            headers=[
                "pipeline",
                "id",
                "passed",
                "output",
                "expected_output",
                "error",
                "duration_seconds",
            ],
            datatype=["str", "str", "bool", "str", "str", "str", "number"],
            interactive=False,
        )

        pipeline_selector.change(_format_pipeline_info, inputs=pipeline_selector, outputs=info_box)
        run_button.click(_run_selected, inputs=pipeline_selector, outputs=[summary_box, results_table])

    return demo


def launch_gradio_app(
    *,
    pipeline: Pipeline | None = None,
    test_cases: Iterable[TestCase] | None = None,
    pipeline_suites: Iterable[PipelineSuite] | None = None,
    comparator: Callable[[Any, Any], bool] | None = None,
    title: str = "Sgr Test Suite",
    description: str | None = None,
    **launch_kwargs: Any,
) -> None:
    """Convenience wrapper that builds and launches the app.

    Передавайте ``pipeline_suites`` при работе с несколькими пайплайнами. Для
    одиночного пайплайна можно использовать более короткую форму через
    ``pipeline`` и ``test_cases``.
    """

    app = build_gradio_app(
        pipeline=pipeline,
        test_cases=test_cases,
        pipeline_suites=pipeline_suites,
        comparator=comparator,
        title=title,
        description=description,
    )
    app.launch(**launch_kwargs)


__all__ = ["PipelineSuite", "build_gradio_app", "launch_gradio_app"]
