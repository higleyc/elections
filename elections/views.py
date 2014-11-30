from django.http import HttpResponse
from django.views import generic
from elections.models import *
from django.template import RequestContext, loader
import logging

logger = logging.getLogger(__name__)

class IndexView(generic.ListView):
    model = ElectionRound
    template_name = "elections/index.html"

def manage_election(request):
    message = ""
    button_message = ""
    election_round = ElectionRound.objects.all()[0]
    next_stage = 0
    
    if request.method == "POST":
        #election_round = ElectionRound.objects.get(id=request.POST.get("round", ""))
        pass
    
    activities = CurrentActivity.objects.filter(election_round=election_round)
    activity = None
    if len(activities) == 0:
        # Init
        activity = CurrentActivity(election_round=election_round, activity=0)
    else:
        activity = activities[0]
    
    if request.method == "POST":
        activity.activity = activity.next_activity
    
    if activity.activity == 0:
        message = "Not yet activated"
        button_message = "Begin"
        if election_round.vote_on_order:
            activity.next_activity = 1
        else:
            activity.next_activity = 5
    elif activity.activity == 1:
        message = "Ready to start ordering change voting"
        button_message = "Start ordering voting"
        activity.next_activity = 2
    elif activity.activity == 2:
        message = "Vote on changing election order open"
        button_message = "Close voting"
        activity.next_activity = 3
    elif activity.activity == 3:
        message = "Ready to start ordering voting"
        button_message = "Start voting"
        activity.next_activity = 4
    elif activity.activity == 4:
        message = "Vote on election order open"
        button_message = "Close voting"
        activity.next_activity = 5
    elif activity.activity == 5:
        if activity.election == None:
            activity.election = Election.objects.filter(election_round=election_round).get(order=1)
            message = "Ready to vote on " + activity.election.__unicode__()
            button_message = "Start voting"
            activity.next_activity = 6
        else:
            elections = Election.objects.filter(election_round=election_round).filter(order=(activity.election.order + 1))
            if len(elections) == 0:
                message = "Elections done!"
                message_button = "Finish"
                activity.next_activity = 7
            else:
                activity.election = elections[0]
                message = "Ready to vote on " + activity.election.__unicode__()
                button_message = "Start voting"
                activity.next_activity = 6
    elif activity.activity == 6:
        message = "Voting on " + activity.election.__unicode__()
        button_message = "Close voting"
        activity.next_activity = 5
    elif activity.activity == 7:
        message = "You're all done"
    
    activity.save()
    
    template = loader.get_template("elections/manage.html")
    context = RequestContext(request, {
        "button_message" : button_message,
        "next_stage" : next_stage,
        "selected_round" : election_round,
        "status_message" : message,
        "round_list" : ElectionRound.objects.all()})
    
    return HttpResponse(template.render(context))