from __future__ import annotations

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


class ExploreService:
    """Compose Explore page modules with feature-flag-aware personalization."""

    def __init__(
        self,
        feature_flags: FeatureFlagService,
        reports_service: ReportsService,
    ) -> None:
        self._feature_flags = feature_flags
        self._reports_service = reports_service

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

    async def _build_breathing_module(self, *, locale: str, reports: JourneyReportsResponse | None = None) -> BreathingExerciseModule:  # noqa: ARG002
        """Return a localized breathing exercise module."""
        if self._is_chinese(locale):
            steps = [
                BreathingStep(label="准备姿势", instruction="坐直或站立，放松肩颈，闭上眼睛。", duration_seconds=10),
                BreathingStep(label="吸气 4 拍", instruction="缓慢用鼻吸气，心中默数 1-2-3-4。", duration_seconds=16),
                BreathingStep(label="屏息 7 拍", instruction="保持肺部充盈，默数 1-7，注意放松肩膀。", duration_seconds=28),
                BreathingStep(label="呼气 8 拍", instruction="通过嘴巴缓慢呼气，感受胸腔逐渐放松。", duration_seconds=32),
            ]
            cadence_label = "4-7-8 呼吸节奏"
            description = "快速缓和心率的放松练习，约 5 分钟即可完成。"
            frequency = "睡前或焦虑感上升时练习 2-3 轮。"
            cta_label = "开始 4-7-8 呼吸"
        else:
            steps = [
                BreathingStep(label="Posture", instruction="Sit or stand tall, relax your shoulders, close your eyes.", duration_seconds=10),
                BreathingStep(label="Inhale 4 Count", instruction="Inhale through the nose while counting 1-2-3-4.", duration_seconds=16),
                BreathingStep(label="Hold 7 Count", instruction="Hold gently for seven beats without tensing your neck.", duration_seconds=28),
                BreathingStep(label="Exhale 8 Count", instruction="Exhale slowly through the mouth, feeling your chest soften.", duration_seconds=32),
            ]
            cadence_label = "4-7-8 cadence"
            description = "A five-minute pace-reset that slows breathing and lowers heart rate."
            frequency = "Practice 2-3 rounds before bed or when anxiety spikes."
            cta_label = "Start breathing guide"

        return BreathingExerciseModule(
            id="breathing-reset",
            title=self._localize(locale, zh="今日呼吸练习", en="Guided Breathing Session"),
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
            themes = self._fallback_themes(locale)

        primary_theme = themes[0]

        if self._is_chinese(locale):
            description = "结合你近期的对话主题，为你精选的心理教育内容。"
            resources = [
                PsychoeducationResource(
                    id="micro-steps",
                    title="把焦虑拆成 3 个可执行微任务",
                    summary="学习如何用具体行动打破焦虑循环，例如呼吸练习、记录触发点和自我肯定。",
                    read_time_minutes=6,
                    tags=[primary_theme, "自我觉察"],
                ),
                PsychoeducationResource(
                    id="sleep-hygiene",
                    title="睡眠节律重建指南",
                    summary="通过晚间放松仪式、光照管理和睡前写作帮助大脑进入休息状态。",
                    read_time_minutes=5,
                    tags=["睡眠卫生", "放松训练"],
                ),
                PsychoeducationResource(
                    id="body-scan",
                    title="3 分钟身体扫描音频",
                    summary="用简短的正念扫描练习快速检测紧绷部位，逐步释放压力。",
                    read_time_minutes=3,
                    tags=["正念练习"],
                    resource_type="audio",
                ),
            ]
            title = "疗愈知识精选"
            cta_label = "查看完整资料"
        else:
            description = "Personalized psychoeducation picks that mirror your recent conversations."
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
            cta_label = "Open resource hub"

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
            topics = self._fallback_themes(locale)

        daily_deltas = [report.mood_delta for report in reports.daily if report.mood_delta is not None]
        average_mood = mean(daily_deltas) if daily_deltas else 0.0
        trend = "up" if average_mood > 0.4 else "down" if average_mood < -0.4 else "steady"
        base_momentum = 68 if trend == "up" else 48 if trend == "steady" else 36

        localized_topics: list[TrendingTopic] = []
        for index, topic in enumerate(topics[:3]):
            adjustment = max(-12, min(12, int(round(average_mood * 10))))
            momentum = max(20, min(95, base_momentum - index * 6 + adjustment))
            summary = (
                f"与你讨论「{topic}」的频率提升，本周可尝试搭配深呼吸或记忆提要。"
                if self._is_chinese(locale)
                else f"Discussions around “{topic}” are gaining traction; pair it with breathing or journaling."
            )
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
            insights = self._fallback_insights(locale)

        title = self._localize(locale, zh="当前关注焦点", en="Trending focus areas")
        description = self._localize(
            locale,
            zh="根据你的近期对话与总结，以下主题最值得继续跟进。",
            en="Based on your latest chats and summaries, these themes deserve extra attention.",
        )

        return TrendingTopicsModule(
            id="trending-topics",
            title=title,
            description=description,
            topics=localized_topics,
            insights=insights[:3],
            cta_label=self._localize(locale, zh="查看练习建议", en="View practice ideas"),
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

    def _fallback_themes(self, locale: str) -> list[str]:
        return (
            ["压力管理", "睡眠节律", "情绪调节"]
            if self._is_chinese(locale)
            else ["Stress management", "Sleep rhythm", "Emotion regulation"]
        )

    def _fallback_insights(self, locale: str) -> list[str]:
        return (
            [
                "保持每晚 10 分钟的放松仪式有助于缩短入睡时间。",
                "记录触发点并练习 4-7-8 呼吸可以在 2 分钟内稳定心率。",
            ]
            if self._is_chinese(locale)
            else [
                "A ten-minute wind-down ritual helps shorten sleep onset time.",
                "Logging triggers plus a 4-7-8 breathing round steadies heart rate within minutes.",
            ]
        )

    def _localize(self, locale: str, *, zh: str, en: str) -> str:
        return zh if self._is_chinese(locale) else en

    def _is_chinese(self, locale: str) -> bool:
        normalized = locale.lower()
        return normalized.startswith("zh")
