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
        
        # set up temp elections
        er_tmp = ElectionRound(name="TMP Order", rule=VotingRuleOption.objects.get(rule=0))
        er_tmp.save()
        election_yesno = Election(name="Change election order", election_round=er_tmp)
        election_order = Election(name="Election order", election_round=er_tmp)
        election_yesno.save()
        election_order.save()
        candidate_yes = Candidate(name="Yes")
        candidate_yes.save()
        candidate_no = Candidate(name="No")
        candidate_no.save()
        election_yesno.candidates.add(candidate_yes)
        election_yesno.candidates.add(candidate_no)
        for election in election_round.election_set.all():
            candidate = Candidate(name=election.name)
            candidate.save()
            election_order.candidates.add(candidate)
        
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
        # temp object cleanup
        if election_round.vote_on_order:
            er_tmp = ElectionRound.objects.get(name="TMP Order")
            for election in er_tmp.election_set.all():
                for candidate in election.candidates:
                    candidate.delete()
                election.delete()
            er_tmp.delete()
                
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

def vote(request):
    election_round = ElectionRound.objects.all()[0]
    status = ""
    is_voting = False
    voting_full_rank = False
    voting_question = ""
    election_id = -1
    options = []
    
    #ACTIVITY IDS
    #0 - pre-start
    #1 - pre do reordering vote
    #2 - do reordering vote open
    #3 - do reordering vote closed
    #4 - reordering vote open
    #5 - pre-vote
    #6 - vote open
    #7 - done
    
    
    activities = CurrentActivity.objects.filter(election_round=election_round)
    if len(activities) == 0:
        status = "Elections are not yet active"
    else:
        activity = activities[0]
        if activity.activity == 0:
            # Pre-start
            status = "Nothing is happening yet - please wait"
        elif activity.activity == 1:
            # pre do reordering vote
            status = "Nothing is happening yet - please wait"
        elif activity.activity == 2:
            # do reordering vote open
            status = "Election reordering vote"
            is_voting = True
            voting_question = "Should the current election order be changed?"
            er_tmp = ElectionRound.objects.get(name="TMP Order")
            election = er_tmp.election_set.get(name="Change election order")
            options = election.candidates.all()
    
    if is_voting and (not voting_full_rank):
        template = loader.get_template("elections/choice_vote.html")
    else:
        template = loader.get_template("elections/vote_base.html")
    context = RequestContext(request, {
        "voting_status" : status,
        "voting_question" : voting_question,
        "options" : options,
        "election_id" : election_id
    })
    
    return HttpResponse(template.render(context))
