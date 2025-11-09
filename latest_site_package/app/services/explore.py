from __future__ import annotations

from collections.abc import Iterable
from statistics import mean

from app.schemas.explore import (
    BreathingExerciseModule,
    BreathingStep,
    ExploreModule,
    ExploreModulesResponse,
    ExploreModuleType,
    PsychoeducationModule,
    PsychoeducationResource,
    TrendingTopic,
    TrendingTopicsModule,
)
from app.schemas.reports import JourneyReportsResponse
from app.services.feature_flags import FeatureFlagService
from app.services.reports import ReportsService
from app.services.translation import TranslationService


class ExploreService:
    """Compose Explore page modules with feature-flag-aware personalization."""

    def __init__(
        self,
        feature_flags: FeatureFlagService,
        reports_service: ReportsService,
        *,
        translator: TranslationService | None = None,
    ) -> None:
        self._feature_flags = feature_flags
        self._reports_service = reports_service
        self._translator = translator

    async def build_modules(self, *, user_id: str, locale: str = "zh-CN") -> ExploreModulesResponse:
        evaluated: dict[str, bool] = {}
        modules: list[ExploreModule] = []
        reports: JourneyReportsResponse | None = None

        async def ensure_reports() -> JourneyReportsResponse:
            nonlocal reports
            if reports is None:
                reports = await self._reports_service.get_reports(user_id)
            return reports

        breathing_enabled = await self._is_enabled("explore_breathing", subject_id=user_id)
        evaluated["explore_breathing"] = breathing_enabled
        if breathing_enabled:
            module = await self._build_breathing_module(locale=locale)
            module.feature_flag = "explore_breathing"
            modules.append(module)

        psychoeducation_enabled = await self._is_enabled("explore_psychoeducation", subject_id=user_id)
        evaluated["explore_psychoeducation"] = psychoeducation_enabled
        if psychoeducation_enabled:
            payload = await ensure_reports()
            module = await self._build_psychoeducation_module(locale=locale, reports=payload)
            module.feature_flag = "explore_psychoeducation"
            modules.append(module)

        trending_enabled = await self._is_enabled("explore_trending", subject_id=user_id)
        evaluated["explore_trending"] = trending_enabled
        if trending_enabled:
            payload = await ensure_reports()
            module = await self._build_trending_module(locale=locale, reports=payload)
            module.feature_flag = "explore_trending"
            modules.append(module)

        return ExploreModulesResponse(locale=locale, modules=modules, evaluated_flags=evaluated)

    async def _build_breathing_module(
        self,
        *,
        locale: str,
        reports: JourneyReportsResponse | None = None,  # noqa: ARG002
    ) -> BreathingExerciseModule:
        """Return a breathing module translated at runtime."""
        step_data = [
            {
                "label": "Posture",
                "instruction": "Sit or stand tall, relax your shoulders, close your eyes.",
                "duration": 10,
            },
            {
                "label": "Inhale 4 Count",
                "instruction": "Inhale through the nose while counting 1-2-3-4.",
                "duration": 16,
            },
            {
                "label": "Hold 7 Count",
                "instruction": "Hold gently for seven beats without tensing your neck.",
                "duration": 28,
            },
            {
                "label": "Exhale 8 Count",
                "instruction": "Exhale slowly through the mouth, feeling your chest soften.",
                "duration": 32,
            },
        ]
        base_strings = {
            "title": "Guided Breathing Session",
            "description": "A five-minute pace-reset that slows breathing and lowers heart rate.",
            "cadence": "4-7-8 cadence",
            "frequency": "Practice 2-3 rounds before bed or when anxiety spikes.",
            "cta": "Start breathing guide",
        }

        if self._should_translate(locale):
            payload: dict[str, str] = {
                "title": base_strings["title"],
                "description": base_strings["description"],
                "cadence": base_strings["cadence"],
                "frequency": base_strings["frequency"],
                "cta": base_strings["cta"],
            }
            for index, step in enumerate(step_data):
                payload[f"step_label_{index}"] = step["label"]
                payload[f"step_instruction_{index}"] = step["instruction"]

            translated = await self._translate_mapping(payload, locale=locale)
            steps = [
                BreathingStep(
                    label=translated[f"step_label_{index}"],
                    instruction=translated[f"step_instruction_{index}"],
                    duration_seconds=step["duration"],
                )
                for index, step in enumerate(step_data)
            ]
            title = translated["title"]
            description = translated["description"]
            cadence_label = translated["cadence"]
            frequency = translated["frequency"]
            cta_label = translated["cta"]
        else:
            steps = [
                BreathingStep(
                    label=step["label"],
                    instruction=step["instruction"],
                    duration_seconds=step["duration"],
                )
                for step in step_data
            ]
            title = base_strings["title"]
            description = base_strings["description"]
            cadence_label = base_strings["cadence"]
            frequency = base_strings["frequency"]
            cta_label = base_strings["cta"]

        return BreathingExerciseModule(
            id="breathing-reset",
            title=title,
            description=description,
            cadence_label=cadence_label,
            steps=steps,
            recommended_frequency=frequency,
            cta_label=cta_label,
            cta_action="/app/practices/breathing",
        )

    async def _build_psychoeducation_module(
        self,
        *,
        locale: str,
        reports: JourneyReportsResponse,
    ) -> PsychoeducationModule:
        """Return psychoeducation articles aligned with recent themes."""
        themes = self._collect_recent_themes(reports)
        if not themes:
            themes = self._fallback_themes()

        primary_theme = themes[0]

        resources = [
            PsychoeducationResource(
                id="micro-steps",
                title="Break anxiety into micro-actions",
                summary="A three-step framework for interrupting anxious spirals with breathing, logging, and reframing.",
                read_time_minutes=6,
                tags=[primary_theme, "self-awareness"],
            ),
            PsychoeducationResource(
                id="sleep-hygiene",
                title="Rebuild your sleep rhythm",
                summary="Design a gentle wind-down routine using light cues, journaling, and body relaxation.",
                read_time_minutes=5,
                tags=["sleep hygiene", "relaxation"],
            ),
            PsychoeducationResource(
                id="body-scan",
                title="Body scan in 3 minutes",
                summary="Short guided audio to locate tension, soften breathing, and re-anchor attention.",
                read_time_minutes=3,
                tags=["mindfulness"],
                resource_type="audio",
            ),
        ]

        title = "Featured psychoeducation"
        description = "Personalized psychoeducation picks that mirror your recent conversations."
        cta_label = "Open resource hub"

        if self._should_translate(locale):
            mapping: dict[str, str] = {
                "title": title,
                "description": description,
                "cta": cta_label,
            }
            for index, resource in enumerate(resources):
                mapping[f"resource_title_{index}"] = resource.title
                mapping[f"resource_summary_{index}"] = resource.summary

            translated = await self._translate_mapping(mapping, locale=locale)
            translated_resources: list[PsychoeducationResource] = []
            for index, resource in enumerate(resources):
                translated_resources.append(
                    PsychoeducationResource(
                        id=resource.id,
                        title=translated[f"resource_title_{index}"],
                        summary=translated[f"resource_summary_{index}"],
                        read_time_minutes=resource.read_time_minutes,
                        tags=await self._translate_list(resource.tags, locale=locale),
                        resource_type=resource.resource_type,
                        url=resource.url,
                    )
                )
            resources = translated_resources
            title = translated["title"]
            description = translated["description"]
            cta_label = translated["cta"]

        return PsychoeducationModule(
            id="psychoeducation",
            title=title,
            description=description,
            resources=resources,
            cta_label=cta_label,
            cta_action="/app/library",
        )

    async def _build_trending_module(
        self,
        *,
        locale: str,
        reports: JourneyReportsResponse,
    ) -> TrendingTopicsModule:
        topics = self._collect_recent_themes(reports)
        if not topics:
            topics = self._fallback_themes()

        daily_deltas = [report.mood_delta for report in reports.daily if report.mood_delta is not None]
        average_mood = mean(daily_deltas) if daily_deltas else 0.0
        trend = "up" if average_mood > 0.4 else "down" if average_mood < -0.4 else "steady"
        base_momentum = 68 if trend == "up" else 48 if trend == "steady" else 36

        localized_topics: list[TrendingTopic] = []
        topic_names = topics[:3]
        summaries: list[str] = []
        for index, topic in enumerate(topic_names):
            adjustment = max(-12, min(12, int(round(average_mood * 10))))
            momentum = max(20, min(95, base_momentum - index * 6 + adjustment))
            summary = f'Discussions around "{topic}" are gaining traction; pair it with breathing or journaling.'
            summaries.append(summary)
            localized_topics.append(
                TrendingTopic(
                    name=topic,
                    momentum=momentum,
                    trend=trend,  # type: ignore[arg-type]
                    summary=summary,
                )
            )

        insights: list[str] = []
        if reports.daily:
            insights.append(reports.daily[0].spotlight)
        if reports.weekly:
            insights.append(reports.weekly[0].highlights)
        if not insights:
            insights = self._fallback_insights()

        title = "Trending focus areas"
        description = (
            "Based on your latest chats and summaries, these themes deserve extra attention."
        )
        cta_label = "View practice ideas"

        if self._should_translate(locale):
            mapping = {
                "title": title,
                "description": description,
                "cta": cta_label,
            }
            translated = await self._translate_mapping(mapping, locale=locale)
            translated_names = await self._translate_list(topic_names, locale=locale)
            translated_summaries = await self._translate_list(summaries, locale=locale)
            translated_insights = await self._translate_list(insights, locale=locale)

            localized_topics = [
                TrendingTopic(
                    name=translated_names[index],
                    momentum=topic.momentum,
                    trend=topic.trend,
                    summary=translated_summaries[index],
                )
                for index, topic in enumerate(localized_topics)
            ]
            insights = translated_insights
            title = translated["title"]
            description = translated["description"]
            cta_label = translated["cta"]

        return TrendingTopicsModule(
            id="trending-topics",
            title=title,
            description=description,
            topics=localized_topics,
            insights=insights[:3],
            cta_label=cta_label,
            cta_action="/app/trends",
        )

    async def _is_enabled(self, key: str, *, subject_id: str | None) -> bool:
        try:
            evaluation = await self._feature_flags.evaluate_flag(key, subject_id=subject_id)
        except ValueError:
            return True
        return evaluation.enabled

    def _collect_recent_themes(self, reports: JourneyReportsResponse) -> list[str]:
        themes: list[str] = []
        for weekly in reports.weekly:
            for theme in weekly.themes:
                normalized = theme.strip()
                if not normalized or normalized in themes:
                    continue
                themes.append(normalized)
                if len(themes) >= 4:
                    break
            if len(themes) >= 4:
                break
        return themes

    def _fallback_themes(self) -> list[str]:
        return ["Stress management", "Sleep rhythm", "Emotion regulation"]

    def _fallback_insights(self) -> list[str]:
        return [
            "A ten-minute wind-down ritual helps shorten sleep onset time.",
            "Logging triggers plus a 4-7-8 breathing round steadies heart rate within minutes.",
        ]

    def _should_translate(self, locale: str) -> bool:
        if not self._translator:
            return False
        return not self._translator.are_locales_equivalent(locale, "en-US")

    async def _translate_list(self, values: Iterable[str], *, locale: str) -> list[str]:
        items = list(values)
        if not items or not self._should_translate(locale):
            return items
        assert self._translator is not None
        return await self._translator.translate_list(
            items,
            target_locale=locale,
            source_locale="en-US",
        )

    async def _translate_mapping(self, mapping: dict[str, str], *, locale: str) -> dict[str, str]:
        if not mapping:
            return {}
        if not self._should_translate(locale):
            return dict(mapping)
        assert self._translator is not None
        keys = list(mapping.keys())
        values = [mapping[key] for key in keys]
        translated_values = await self._translator.translate_list(
            values,
            target_locale=locale,
            source_locale="en-US",
        )
        return {key: translated_values[index] for index, key in enumerate(keys)}
