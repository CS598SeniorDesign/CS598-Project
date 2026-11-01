from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from recommendations.evaluation import feedback_metrics, feedback_summary
from recommendations.experiments import log_run


class Command(BaseCommand):
    """
    Report how users reacted to recommendations: likes, dislikes, and like rate per strategy.

    Prints a table and sends the numbers to the experiment trackers in ``RECOMMENDER_TRACKERS``, so like rates can be
    charted over time and compared across strategies. Run it on a schedule alongside ``train_recommender``.
    """

    help = "Reports recommendation feedback per strategy to the console and the experiment trackers."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30, help="How many days of feedback to include (default 30).")

    def handle(self, *args, **options):
        """
        Summarize and report recent feedback.

        :param args: Additional positional arguments.
        :param options: Parsed command options.
        :returns: None
        """
        days = options["days"]
        summary = feedback_summary(timezone.now() - timedelta(days=days))

        if summary.empty:
            self.stdout.write(f"No recommendation feedback in the last {days} days.")
        else:
            self.stdout.write(f"Recommendation feedback, last {days} days:")
            self.stdout.write(f"{'strategy':<24}{'likes':>8}{'dislikes':>10}{'like rate':>11}")
            for row in summary.itertuples():
                self.stdout.write(f"{row.strategy:<24}{row.likes:>8}{row.dislikes:>10}{row.like_rate:>11.1%}")

        trackers = log_run("recommendation_report", {"days": days}, feedback_metrics(summary), {"job": "feedback"})
        self.stdout.write(f"Report sent to: {', '.join(trackers) or 'no trackers'}.")
