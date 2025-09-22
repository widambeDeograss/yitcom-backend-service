from django.db.models.functions.datetime import TruncMonth

from ..models import User
from ...blogs.models import Blog
from ...events.models import Event, EventTicket
from ...forums.models import Forum, Discussion, Comment, Reaction
from ...projects.models import Project
from datetime import datetime, timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count



class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        current_year = datetime.now().year
        try:
            total_users = User.objects.all().count()

            total_events = Event.objects.all().count()

            total_forums = Forum.objects.all().count()

            total_blogs = Blog.objects.all().count()

            total_projects = Project.objects.all().count()

            # Total Revenue
            # total_revenue = EventTicket.objects.filter( date_received__year=current_year).aggregate(
            #     total=Sum('amount')
            # )['total'] or 0


            data = {
                "total_users": total_users,
                "total_events": total_events,
                "total_blogs": total_blogs,
                "total_projects": total_projects,
                "forums":total_forums
            }
            return Response(data, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=500)



class UserRegistrationStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        period = request.query_params.get("period", "Monthly")

        if period == "Monthly":
            data = self.get_monthly_user_stats()
        else:
            data = []  # you can extend later for Weekly, Yearly, etc.

        return Response(data)

    def get_monthly_user_stats(self):
        current_year = datetime.now().year

        registrations = (
            User.objects.filter(created_at__year=current_year)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(total=Count("id"))
            .order_by("month")
        )

        return [
            {
                "name": reg["month"].strftime("%B"),  # "January", "February", etc.
                "total": reg["total"] or 0,
            }
            for reg in registrations
        ]



class ForumsRegistrationStatsView(APIView):
    permission_classes = [IsAuthenticated]
    """
    Returns overall forum engagement (Discussions, Comments, Reactions)
    for the admin dashboard pie chart.
    """

    def get(self, request):
        discussions_count = Discussion.objects.count()
        comments_count = Comment.objects.count()
        reactions_count = Reaction.objects.count()

        data = [
            ["Discussions", discussions_count],
            ["Comments", comments_count],
            ["Reactions", reactions_count],
        ]

        return Response(data)
