from datetime import datetime
from typing import Iterable, List, Tuple

from httpx import AsyncClient, BasicAuth, HTTPStatusError

from app.core.clickhouse import get_clickhouse_client
from app.core.config import settings
from app.models.metric import MetricName


def _ts(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat()


class MetricQueryBuilder:
    """Строит SQL ClickHouse для агрегированных метрик. TODO: сверить формулы с дипломом."""

    @staticmethod
    def retention(start: datetime, end: datetime, course_id: str) -> str:
        return f"""
        SELECT user_id,
               toFloat64(countDistinct(toDate(timestamp)) > 1) AS value
        FROM {settings.clickhouse_events_table}
        WHERE course_id = '{course_id}'
          AND timestamp >= toDateTime('{_ts(start)}')
          AND timestamp < toDateTime('{_ts(end)}')
        GROUP BY user_id
        FORMAT JSON
        """

    @staticmethod
    def engagement(start: datetime, end: datetime, course_id: str) -> str:
        # Весовой скоринг событий; подлежит уточнению
        return f"""
        SELECT user_id,
               sum(
                   multiIf(
                       event_type = 'page_view', 1.0,
                       event_type = 'scroll', 0.2,
                       event_type = 'video_play', 1.5,
                       event_type = 'task_attempt', 2.0,
                       event_type = 'task_start', 1.0,
                       event_type = 'task_success', 2.5,
                       event_type = 'task_fail', 1.5,
                       0.0
                   )
               ) AS value
        FROM {settings.clickhouse_events_table}
        WHERE course_id = '{course_id}'
          AND timestamp >= toDateTime('{_ts(start)}')
          AND timestamp < toDateTime('{_ts(end)}')
        GROUP BY user_id
        FORMAT JSON
        """

    @staticmethod
    def completion(start: datetime, end: datetime, course_id: str) -> str:
        return f"""
        WITH attempts AS (
            SELECT user_id,
                   sum(event_type = 'task_success') AS success_cnt,
                   sum(event_type = 'task_fail') AS fail_cnt
            FROM {settings.clickhouse_events_table}
            WHERE course_id = '{course_id}'
              AND timestamp >= toDateTime('{_ts(start)}')
              AND timestamp < toDateTime('{_ts(end)}')
            GROUP BY user_id
        )
        SELECT user_id,
               if(success_cnt + fail_cnt = 0, 0.0, success_cnt / (success_cnt + fail_cnt)) AS value
        FROM attempts
        FORMAT JSON
        """

    @staticmethod
    def time_on_task(start: datetime, end: datetime, course_id: str) -> str:
        # Сумма времени от task_start до следующего события пользователя (секунды, cap 30 мин)
        return f"""
        WITH ordered AS (
            SELECT
                user_id,
                event_type,
                timestamp,
                lead(timestamp, 1) OVER (PARTITION BY user_id ORDER BY timestamp) AS next_ts
            FROM {settings.clickhouse_events_table}
            WHERE course_id = '{course_id}'
              AND timestamp >= toDateTime('{_ts(start)}')
              AND timestamp < toDateTime('{_ts(end)}')
        )
        SELECT user_id,
               sum(
                   greatest(
                       0,
                       least(1800, dateDiff('second', timestamp, next_ts))
                   )
               ) AS value
        FROM ordered
        WHERE event_type = 'task_start'
        GROUP BY user_id
        FORMAT JSON
        """

    @staticmethod
    def activity_index(start: datetime, end: datetime, course_id: str) -> str:
        return f"""
        WITH per_user AS (
            SELECT
                user_id,
                min(timestamp) AS first_ts,
                max(timestamp) AS last_ts,
                count() AS events_cnt
            FROM {settings.clickhouse_events_table}
            WHERE course_id = '{course_id}'
              AND timestamp >= toDateTime('{_ts(start)}')
              AND timestamp < toDateTime('{_ts(end)}')
            GROUP BY user_id
        )
        SELECT
            user_id,
            events_cnt / greatest(1, dateDiff('day', first_ts, last_ts) + 1) AS value
        FROM per_user
        FORMAT JSON
        """

    @staticmethod
    def focus_ratio(start: datetime, end: datetime, course_id: str) -> str:
        return f"""
        WITH spans AS (
            SELECT
                user_id,
                min(timestamp) AS first_ts,
                max(timestamp) AS last_ts
            FROM {settings.clickhouse_events_table}
            WHERE course_id = '{course_id}'
              AND timestamp >= toDateTime('{_ts(start)}')
              AND timestamp < toDateTime('{_ts(end)}')
            GROUP BY user_id
        ),
        task_time AS (
            SELECT user_id,
                   sum(
                       greatest(
                           0,
                           least(1800, dateDiff('second', timestamp,
                               lead(timestamp, 1) OVER (PARTITION BY user_id ORDER BY timestamp)
                           ))
                       )
                   ) AS time_on_task
            FROM {settings.clickhouse_events_table}
            WHERE course_id = '{course_id}'
              AND timestamp >= toDateTime('{_ts(start)}')
              AND timestamp < toDateTime('{_ts(end)}')
            GROUP BY user_id
        )
        SELECT
            spans.user_id,
            if(
                dateDiff('second', spans.first_ts, spans.last_ts) <= 0,
                0.0,
                time_on_task / dateDiff('second', spans.first_ts, spans.last_ts)
            ) AS value
        FROM spans
        LEFT JOIN task_time USING (user_id)
        FORMAT JSON
        """

    @staticmethod
    def build(metric: MetricName, start: datetime, end: datetime, course_id: str) -> str:
        builders = {
            MetricName.RETENTION: MetricQueryBuilder.retention,
            MetricName.ENGAGEMENT: MetricQueryBuilder.engagement,
            MetricName.COMPLETION: MetricQueryBuilder.completion,
            MetricName.TIME_ON_TASK: MetricQueryBuilder.time_on_task,
            MetricName.ACTIVITY_INDEX: MetricQueryBuilder.activity_index,
            MetricName.FOCUS_RATIO: MetricQueryBuilder.focus_ratio,
        }
        if metric not in builders:
            raise ValueError(f"Unsupported metric: {metric}")
        return builders[metric](start, end, course_id)


class ClickHouseMetricRepository:
    """Выполняет агрегационные запросы в ClickHouse."""

    def __init__(self, client_provider=get_clickhouse_client):
        self.client_provider = client_provider

    async def fetch_metric(
        self,
        metric: MetricName,
        start: datetime,
        end: datetime,
        course_id: str,
    ) -> List[Tuple[str, float]]:
        client: AsyncClient = self.client_provider()
        query = MetricQueryBuilder.build(metric, start, end, course_id)
        auth = (
            BasicAuth(settings.clickhouse_user, settings.clickhouse_password)
            if settings.clickhouse_password
            else None
        )
        response = await client.post(
            "/",
            params={"database": settings.clickhouse_database, "query": query},
            auth=auth,
        )
        try:
            response.raise_for_status()
        except HTTPStatusError as exc:
            detail = exc.response.text
            raise RuntimeError(f"ClickHouse metrics query failed: {detail}") from exc

        payload = response.json()
        data = payload.get("data", [])
        return [(row["user_id"], float(row["value"])) for row in data]
