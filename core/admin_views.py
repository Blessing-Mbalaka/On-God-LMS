from __future__ import annotations

from datetime import timedelta
from typing import Dict, List

from django.contrib.auth.decorators import login_required
from django.db.models import (
    Avg,
    Count,
    F,
    FloatField,
    Max,
    Q,
)
from django.db.models import ExpressionWrapper
from django.db.models.functions import TruncMonth, TruncWeek
from django.shortcuts import render
from django.utils import timezone

from .models import (
    Assessment,
    CustomUser,
    ExamSubmission,
    Paper,
    PaperBankEntry,
    Qualification,
)

PASS_THRESHOLD = 0.5  # 50% cutoff for pass-rate metrics
COMPLETED_STATUSES = {
    "moderated",
    "etqa_approved",
    "qcto_approved",
    "Released to students",
    "archived",
}


def _resolve_period(period_key: str | None) -> tuple[str, int]:
    period_options = {
        "30d": ("Last 30 days", 30),
        "90d": ("Last 90 days", 90),
        "365d": ("Last 12 months", 365),
    }
    if period_key in period_options:
        label, days = period_options[period_key]
    else:
        label, days = period_options["30d"]
        period_key = "30d"
    return period_key, days


def _safe_int(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


def _localize(dt):
    if not dt:
        return None
    if timezone.is_aware(dt):
        return timezone.localtime(dt)
    return dt


def _format_latest_assessment(assessment: Assessment | None) -> str | None:
    if not assessment:
        return None
    parts = [assessment.paper]
    if assessment.eisa_id:
        parts.append(f"({assessment.eisa_id})")
    return " ".join(filter(None, parts))


@login_required
def administrator_analytics_dashboard(request):
    period_key, period_days = _resolve_period(request.GET.get("period"))
    qualification_id = _safe_int(request.GET.get("qualification"))
    paper_type = request.GET.get("paper_type") or ""

    now = timezone.now()
    current_start = now - timedelta(days=period_days)
    previous_start = current_start - timedelta(days=period_days)

    assessments_base = Assessment.objects.select_related("qualification", "paper_link")
    exam_submissions_base = ExamSubmission.objects.select_related("assessment__qualification")
    learner_users = CustomUser.objects.filter(role="learner")

    if qualification_id:
        assessments_base = assessments_base.filter(qualification_id=qualification_id)
        exam_submissions_base = exam_submissions_base.filter(assessment__qualification_id=qualification_id)
        learner_users = learner_users.filter(qualification_id=qualification_id)

    if paper_type:
        assessments_base = assessments_base.filter(paper_type=paper_type)
        exam_submissions_base = exam_submissions_base.filter(assessment__paper_type=paper_type)

    assessments_current = assessments_base.filter(created_at__gte=current_start)
    assessments_previous = assessments_base.filter(created_at__gte=previous_start, created_at__lt=current_start)

    submissions_current = exam_submissions_base.filter(submitted_at__gte=current_start)
    submissions_previous = exam_submissions_base.filter(submitted_at__gte=previous_start, submitted_at__lt=current_start)

    total_learners = learner_users.count()
    active_qualifications = (
        learner_users.exclude(qualification__isnull=True).values("qualification").distinct().count()
    )

    current_completed = assessments_current.filter(status__in=COMPLETED_STATUSES).count()
    previous_completed = assessments_previous.filter(status__in=COMPLETED_STATUSES).count()
    completed_delta = None
    if previous_completed:
        completed_delta = ((current_completed - previous_completed) / previous_completed) * 100

    pass_summary_current = submissions_current.filter(
        marks__isnull=False, total_marks__gt=0
    ).aggregate(
        total=Count("id"),
        passed=Count("id", filter=Q(marks__gte=F("total_marks") * PASS_THRESHOLD)),
    )
    pass_summary_previous = submissions_previous.filter(
        marks__isnull=False, total_marks__gt=0
    ).aggregate(
        total=Count("id"),
        passed=Count("id", filter=Q(marks__gte=F("total_marks") * PASS_THRESHOLD)),
    )

    current_total = pass_summary_current["total"] or 0
    current_passed = pass_summary_current["passed"] or 0
    previous_total = pass_summary_previous["total"] or 0
    previous_passed = pass_summary_previous["passed"] or 0

    overall_pass_rate = (current_passed / current_total) * 100 if current_total else 0.0
    pass_rate_delta = None
    if previous_total:
        previous_rate = (previous_passed / previous_total) * 100
        pass_rate_delta = overall_pass_rate - previous_rate

    paper_ids = assessments_current.filter(
        paper_link__isnull=False
    ).values_list("paper_link_id", flat=True).distinct()
    papers_qs = Paper.objects.filter(id__in=paper_ids)
    randomized_papers = papers_qs.filter(is_randomized=True).count()
    total_papers = papers_qs.count()
    randomized_share = (randomized_papers / total_papers) * 100 if total_papers else 0.0

    metrics = {
        "total_learners": total_learners,
        "active_qualifications": active_qualifications,
        "completed_assessments": current_completed,
        "completed_assessments_delta": completed_delta,
        "overall_pass_rate": overall_pass_rate,
        "pass_rate_delta": pass_rate_delta,
        "randomized_papers": randomized_papers,
        "randomized_share": randomized_share,
    }

    pass_rate_rows = (
        submissions_current.filter(marks__isnull=False, total_marks__gt=0)
        .values("assessment__qualification__name")
        .annotate(
            total=Count("id"),
            passed=Count("id", filter=Q(marks__gte=F("total_marks") * PASS_THRESHOLD)),
        )
        .order_by("-total")
    )
    pass_rate_data: List[Dict[str, float | str]] = []
    for row in pass_rate_rows:
        total = row["total"] or 0
        passed = row["passed"] or 0
        if not total:
            continue
        pass_rate_data.append(
            {
                "qualification": row["assessment__qualification__name"] or "Unassigned",
                "pass_rate": round((passed / total) * 100, 1),
            }
        )

    trunc_fn = TruncWeek if period_days <= 90 else TruncMonth
    completion_trend_rows = (
        assessments_base.filter(status__in=COMPLETED_STATUSES, created_at__gte=current_start)
        .annotate(period=trunc_fn("created_at"))
        .values("period")
        .annotate(completed=Count("id"))
        .order_by("period")
    )
    completion_trend_data: List[Dict[str, str | int]] = []
    for row in completion_trend_rows:
        period = row["period"]
        if not period:
            continue
        localized = _localize(period)
        label = localized.strftime("%b %d, %Y") if period_days <= 90 else localized.strftime("%b %Y")
        completion_trend_data.append({"label": label, "completed": row["completed"]})

    assessment_type_rows = (
        assessments_current.values("paper_type").annotate(total=Count("id")).order_by("paper_type")
    )
    assessment_type_breakdown: Dict[str, int] = {}
    type_labels = dict(Assessment.PAPER_TYPE_CHOICES)
    for row in assessment_type_rows:
        key = row["paper_type"] or "unknown"
        label = type_labels.get(key, key.title())
        assessment_type_breakdown[label] = row["total"]

    enrollment_rows = (
        learner_users.values("qualification__name")
        .annotate(total=Count("id"))
        .order_by("-total", "qualification__name")
    )
    enrollment_by_course_data = [
        {
            "qualification": row["qualification__name"] or "Unassigned",
            "learners": row["total"],
        }
        for row in enrollment_rows
    ][:12]

    learners_map = {
        row["qualification_id"]: row["total"]
        for row in learner_users.values("qualification_id").annotate(total=Count("id"))
    }

    completed_learners_map = {
        row["assessment__qualification_id"]: row["unique_learners"]
        for row in submissions_current.filter(student_number__isnull=False)
        .values("assessment__qualification_id")
        .annotate(unique_learners=Count("student_number", distinct=True))
    }

    score_expression = ExpressionWrapper(
        F("marks") * 100.0 / F("total_marks"),
        output_field=FloatField(),
    )
    avg_score_rows = (
        submissions_current.filter(total_marks__gt=0, marks__isnull=False)
        .annotate(score_pct=score_expression)
        .values("assessment__qualification_id")
        .annotate(avg_score=Avg("score_pct"))
    )
    avg_score_map = {
        row["assessment__qualification_id"]: row["avg_score"] for row in avg_score_rows
    }

    pass_rate_map = {
        row["assessment__qualification_id"]: (
            (row["passed"] / row["total"]) * 100 if row["total"] else None
        )
        for row in (
            submissions_current.filter(total_marks__gt=0, marks__isnull=False)
            .values("assessment__qualification_id")
            .annotate(
                total=Count("id"),
                passed=Count("id", filter=Q(marks__gte=F("total_marks") * PASS_THRESHOLD)),
            )
        )
    }

    assessment_counts = (
        assessments_current.values("qualification_id", "qualification__name")
        .annotate(
            written_count=Count("id", filter=Q(paper_type="admin_upload")),
            randomized_count=Count("id", filter=Q(paper_type="randomized")),
            total=Count("id"),
            latest_created=Max("created_at"),
        )
        .order_by("qualification__name")
    )

    latest_assessment_map: Dict[int | None, str | None] = {}
    for assessment in assessments_current.order_by("-created_at"):
        qid = assessment.qualification_id
        if qid not in latest_assessment_map:
            latest_assessment_map[qid] = _format_latest_assessment(assessment)

    course_statistics: List[Dict[str, object]] = []
    for row in assessment_counts:
        qid = row["qualification_id"]
        course_statistics.append(
            {
                "qualification": row["qualification__name"] or "Unassigned",
                "total_learners": learners_map.get(qid, 0),
                "completed_learners": completed_learners_map.get(qid, 0),
                "pass_rate": pass_rate_map.get(qid),
                "average_score": avg_score_map.get(qid),
                "written_count": row["written_count"],
                "randomized_count": row["randomized_count"],
                "latest_assessment": latest_assessment_map.get(qid),
            }
        )

    context = {
        "metrics": metrics,
        "qualifications": Qualification.objects.all().order_by("name"),
        "assessment_type_choices": Assessment.PAPER_TYPE_CHOICES,
        "period_options": [
            ("30d", "Last 30 days"),
            ("90d", "Last 90 days"),
            ("365d", "Last 12 months"),
        ],
        "pass_rate_data": pass_rate_data,
        "completion_trend_data": completion_trend_data,
        "assessment_type_breakdown": assessment_type_breakdown,
        "enrollment_by_course_data": enrollment_by_course_data,
        "course_statistics": course_statistics,
        "active_page": "analytics-dashboard",
    }
    context["request"] = request
    return render(request, "core/administrator/dashboards.html", context)


@login_required
def administrator_paperbank(request):
    qualification_id = _safe_int(request.GET.get("qualification"))
    paper_type = request.GET.get("paper_type") or ""
    status_filter = request.GET.get("status") or ""
    query = (request.GET.get("q") or "").strip()

    entries_qs = PaperBankEntry.objects.select_related(
        "assessment",
        "assessment__qualification",
        "assessment__paper_link",
        "assessment__paper_link__created_by",
    ).order_by("-created_at")

    if qualification_id:
        entries_qs = entries_qs.filter(assessment__qualification_id=qualification_id)

    if paper_type:
        entries_qs = entries_qs.filter(assessment__paper_type=paper_type)

    if status_filter:
        entries_qs = entries_qs.filter(assessment__status=status_filter)

    if query:
        entries_qs = entries_qs.filter(
            Q(assessment__eisa_id__icontains=query)
            | Q(assessment__paper__icontains=query)
        )

    total_entries = entries_qs.count()
    aggregates = entries_qs.aggregate(
        randomized_entries=Count(
            "id",
            filter=Q(assessment__paper_link__is_randomized=True)
            | Q(assessment__paper_type="randomized"),
        ),
        memos_available=Count(
            "id",
            filter=Q(assessment__memo__isnull=False)
            | Q(assessment__memo_file__isnull=False),
        ),
        latest_upload_at=Max("created_at"),
        average_total_marks=Avg(
            "assessment__paper_link__total_marks",
            filter=Q(assessment__paper_link__total_marks__isnull=False),
            output_field=FloatField(),
        ),
    )

    randomized_entries = aggregates["randomized_entries"] or 0
    memos_available = aggregates["memos_available"] or 0
    latest_upload_at = aggregates["latest_upload_at"]
    average_total_marks = aggregates["average_total_marks"]

    paperbank_stats = {
        "total_entries": total_entries,
        "randomized_entries": randomized_entries,
        "randomized_share": (randomized_entries / total_entries) * 100 if total_entries else 0.0,
        "memos_available": memos_available,
        "memos_share": (memos_available / total_entries) * 100 if total_entries else 0.0,
        "latest_upload_at": _localize(latest_upload_at).strftime("%Y-%m-%d %H:%M") if latest_upload_at else None,
        "average_total_marks": average_total_marks,
    }

    uploads_by_month_rows = (
        entries_qs.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )
    uploads_by_month = [
        {"label": _localize(row["month"]).strftime("%b %Y"), "count": row["count"]}
        for row in uploads_by_month_rows
        if row["month"]
    ]

    distribution_rows = (
        entries_qs.values("assessment__qualification__name")
        .annotate(count=Count("id"))
        .order_by("-count", "assessment__qualification__name")
    )
    paperbank_distribution = [
        {
            "qualification": row["assessment__qualification__name"] or "Unassigned",
            "count": row["count"],
        }
        for row in distribution_rows
    ]

    context = {
        "qualifications": Qualification.objects.all().order_by("name"),
        "paper_type_choices": Assessment.PAPER_TYPE_CHOICES,
        "status_options": Assessment.STATUS_CHOICES,
        "paperbank_stats": paperbank_stats,
        "uploads_by_month": uploads_by_month,
        "paperbank_distribution": paperbank_distribution,
        "paper_bank_entries": entries_qs,
        "active_page": "paper-bank",
    }
    context["request"] = request
    return render(request, "core/administrator/paperbank.html", context)
