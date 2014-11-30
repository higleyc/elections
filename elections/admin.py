from django.contrib import admin
from elections.models import ElectionRound, Election, Candidate, Vote, CurrentActivity

class ElectionAdminInline(admin.TabularInline):
    model = Election
    extra = 1


class ElectionRoundAdmin(admin.ModelAdmin):
    fields = ["name", "description", "rule", "vote_on_order", "order_vote_margin"]
    inlines = [ElectionAdminInline]
    list_display = ("name", "description")
    search_fields = ["name"]

class ElectionAdmin(admin.ModelAdmin):
    fields = ["name", "description", "election_round", "candidates"]


admin.site.register(ElectionRound, ElectionRoundAdmin)
admin.site.register(Election, ElectionAdmin)
admin.site.register(Candidate)
admin.site.register(Vote)
admin.site.register(CurrentActivity)